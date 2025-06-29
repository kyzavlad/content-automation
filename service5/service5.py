import os
import json
import logging
import time
import random
from datetime import datetime
from flask import Flask, request, jsonify
import subprocess
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

# Load accounts configuration
ACCOUNTS_FILE = '/app/accounts-config.json'
if os.path.exists(ACCOUNTS_FILE):
    with open(ACCOUNTS_FILE, 'r') as f:
        ACCOUNTS_CONFIG = json.load(f)
else:
    ACCOUNTS_CONFIG = {"platforms": {"youtube": {"accounts": []}}}

def get_youtube_accounts():
    """Get configured YouTube accounts"""
    accounts = ACCOUNTS_CONFIG.get('platforms', {}).get('youtube', {}).get('accounts', [])
    
    # Filter valid accounts
    valid_accounts = []
    for account in accounts:
        if (account.get('username') and 
            account.get('username') != 'ЗАПОЛНИТЬ' and
            account.get('credentials_file')):  # Need OAuth2 credentials
            valid_accounts.append(account)
    
    return valid_accounts

def get_youtube_service(account):
    """Create YouTube API service for account"""
    try:
        # Load credentials from account config
        if account.get('service_account_key'):
            # Service account authentication
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(account['service_account_key']),
                scopes=['https://www.googleapis.com/auth/youtube.upload']
            )
        elif account.get('oauth2_credentials'):
            # OAuth2 authentication
            from google.oauth2.credentials import Credentials
            credentials = Credentials.from_authorized_user_info(
                json.loads(account['oauth2_credentials']),
                scopes=['https://www.googleapis.com/auth/youtube.upload']
            )
        else:
            raise Exception("No valid credentials found for account")
        
        # Build service
        youtube = build('youtube', 'v3', credentials=credentials)
        return youtube
        
    except Exception as e:
        logging.error(f"Error creating YouTube service: {str(e)}")
        return None

def generate_thumbnail(video_path, output_path, timestamp="00:00:05"):
    """Generate thumbnail from video"""
    cmd = f'ffmpeg -y -ss {timestamp} -i "{video_path}" -vframes 1 -vf "scale=1280:720" "{output_path}"'
    subprocess.run(cmd, shell=True, capture_output=True)
    return os.path.exists(output_path)

def optimize_video_for_youtube(input_path, output_path):
    """Optimize video for YouTube upload"""
    cmd = f'''ffmpeg -y -i "{input_path}" \
    -c:v libx264 -preset slow -crf 18 \
    -c:a aac -b:a 192k -ar 48000 \
    -vf "scale='if(gt(iw\\,ih)\\,min(1920\\,iw)\\,-2)':'if(gt(iw\\,ih)\\,-2\\,min(1080\\,ih))'" \
    -movflags +faststart \
    -metadata:s:v:0 language=eng \
    -metadata:s:a:0 language=eng \
    "{output_path}"'''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0

def upload_video_to_youtube(youtube_service, video_path, metadata):
    """Upload video using YouTube API"""
    try:
        # Video metadata
        body = {
            'snippet': {
                'title': metadata['title'],
                'description': metadata['description'],
                'tags': metadata.get('tags', []),
                'categoryId': '22',  # People & Blogs
                'defaultLanguage': 'en',
                'defaultAudioLanguage': 'en'
            },
            'status': {
                'privacyStatus': metadata.get('privacy', 'public'),
                'selfDeclaredMadeForKids': False,
                'embeddable': True,
                'publicStatsViewable': True
            }
        }
        
        # Call the API's videos.insert method to create and upload the video
        insert_request = youtube_service.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/mp4'
            )
        )
        
        # Execute upload
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                logging.info(f"Uploading video: {metadata['title']}")
                status, response = insert_request.next_chunk()
                
                if status:
                    logging.info(f"Upload progress: {int(status.progress() * 100)}%")
                    
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Retry on server errors
                    error = f"Server error: {e}"
                    retry += 1
                    if retry > 3:
                        raise
                    
                    time.sleep(5 * retry)
                else:
                    raise
            except Exception as e:
                error = f"Upload error: {e}"
                raise
        
        if response is not None:
            video_id = response.get('id')
            
            # Upload thumbnail if provided
            if metadata.get('thumbnail') and os.path.exists(metadata['thumbnail']):
                try:
                    youtube_service.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(metadata['thumbnail'])
                    ).execute()
                    logging.info(f"Thumbnail uploaded for video {video_id}")
                except Exception as e:
                    logging.error(f"Thumbnail upload failed: {str(e)}")
            
            return {
                'status': 'success',
                'video_id': video_id,
                'url': f"https://youtube.com/watch?v={video_id}"
            }
        else:
            return {
                'status': 'failed',
                'error': error or 'Unknown error'
            }
            
    except Exception as e:
        logging.error(f"YouTube upload error: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }

@app.route('/health', methods=['GET'])
def health():
    accounts = get_youtube_accounts()
    
    # Test API connectivity
    api_status = {}
    for account in accounts[:1]:  # Test first account only
        service = get_youtube_service(account)
        if service:
            try:
                # Test API call
                service.channels().list(part='id', mine=True).execute()
                api_status[account['id']] = 'connected'
            except:
                api_status[account['id']] = 'error'
        else:
            api_status[account['id']] = 'no_service'
    
    return jsonify({
        'status': 'ok',
        'service': 'youtube-publisher',
        'configured_accounts': len(accounts),
        'accounts': [a['id'] for a in accounts],
        'api_status': api_status
    })

@app.route('/publish-long', methods=['POST'])
def publish_long():
    """Publish long video to YouTube with SEO optimization"""
    try:
        data = request.json
        video_path = data.get('video') or data.get('videoPath')
        seo_variations = data.get('seo_variations', [])
        
        if not video_path:
            return jsonify({'error': 'Video path is required'}), 400
        
        if not os.path.exists(video_path):
            return jsonify({'error': f'Video not found: {video_path}'}), 404
        
        # Get YouTube accounts
        accounts = get_youtube_accounts()
        if not accounts:
            return jsonify({
                'error': 'No YouTube accounts configured',
                'message': 'Please configure YouTube accounts with API credentials'
            }), 400
        
        # If no SEO variations provided, create default
        if not seo_variations:
            seo_variations = [{
                'title': 'Motivational Video',
                'description': 'Watch this inspiring content',
                'tags': ['motivation', 'success', 'mindset']
            }] * len(accounts)
        
        # Ensure we have enough variations for all accounts
        while len(seo_variations) < len(accounts):
            seo_variations.extend(seo_variations)
        
        results = []
        
        # Process video for YouTube
        optimized_path = f"/data/youtube_optimized_{int(time.time())}.mp4"
        logging.info(f"Optimizing video for YouTube: {video_path}")
        
        if optimize_video_for_youtube(video_path, optimized_path):
            video_to_upload = optimized_path
        else:
            logging.warning("Video optimization failed, using original")
            video_to_upload = video_path
        
        # Generate thumbnail
        thumbnail_path = f"/data/thumbnail_{int(time.time())}.jpg"
        generate_thumbnail(video_to_upload, thumbnail_path)
        
        # Upload to each account with different SEO
        for i, account in enumerate(accounts):
            # Get YouTube service for this account
            youtube_service = get_youtube_service(account)
            if not youtube_service:
                results.append({
                    'platform': 'youtube',
                    'account_id': account['id'],
                    'status': 'failed',
                    'error': 'Could not create YouTube service',
                    'timestamp': datetime.now().isoformat()
                })
                continue
            
            # Get SEO variation for this account
            seo = seo_variations[i % len(seo_variations)]
            
            # Prepare metadata
            metadata = {
                'title': seo.get('title', 'Untitled Video'),
                'description': seo.get('description', ''),
                'tags': seo.get('tags', []),
                'category': seo.get('category', 'People & Blogs'),
                'privacy': 'public',
                'thumbnail': thumbnail_path if os.path.exists(thumbnail_path) else None
            }
            
            # Add delay between uploads
            if i > 0:
                time.sleep(random.uniform(30, 60))
            
            # Upload video
            upload_result = upload_video_to_youtube(youtube_service, video_to_upload, metadata)
            
            results.append({
                'platform': 'youtube',
                'account_id': account['id'],
                **upload_result,
                'metadata': metadata,
                'timestamp': datetime.now().isoformat()
            })
        
        # Cleanup temporary files
        if os.path.exists(optimized_path) and optimized_path != video_path:
            os.remove(optimized_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        
        # Summary
        successful = [r for r in results if r.get('status') == 'success']
        
        return jsonify({
            'status': 'success',
            'results': results,
            'summary': {
                'total_uploads': len(results),
                'successful': len(successful),
                'failed': len(results) - len(successful),
                'accounts_used': [r['account_id'] for r in results],
                'video_urls': [r.get('url') for r in successful if r.get('url')]
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Error in publish_long: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/configure-youtube-account', methods=['POST'])
def configure_youtube_account():
    """Helper endpoint to configure YouTube account credentials"""
    try:
        data = request.json
        account_id = data.get('account_id')
        credentials = data.get('credentials')  # OAuth2 or service account JSON
        
        if not account_id or not credentials:
            return jsonify({'error': 'account_id and credentials required'}), 400
        
        # Find and update account
        for platform in ACCOUNTS_CONFIG['platforms']:
            for account in ACCOUNTS_CONFIG['platforms'][platform].get('accounts', []):
                if account['id'] == account_id:
                    # Detect credential type
                    if 'type' in credentials and credentials['type'] == 'service_account':
                        account['service_account_key'] = json.dumps(credentials)
                    else:
                        account['oauth2_credentials'] = json.dumps(credentials)
                    
                    # Save configuration
                    with open(ACCOUNTS_FILE, 'w') as f:
                        json.dump(ACCOUNTS_CONFIG, f, indent=2)
                    
                    return jsonify({
                        'status': 'success',
                        'message': f'Credentials updated for {account_id}'
                    }), 200
        
        return jsonify({'error': 'Account not found'}), 404
        
    except Exception as e:
        logging.error(f"Error configuring account: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3005, threaded=True)
