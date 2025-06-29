import os
import json
import logging
import time
import random
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

# Load accounts configuration
ACCOUNTS_FILE = '/app/accounts-config.json'
if os.path.exists(ACCOUNTS_FILE):
    with open(ACCOUNTS_FILE, 'r') as f:
        ACCOUNTS_CONFIG = json.load(f)
else:
    ACCOUNTS_CONFIG = {"platforms": {}}

def validate_accounts():
    """Check which accounts are properly configured"""
    valid_accounts = {}
    
    for platform, data in ACCOUNTS_CONFIG['platforms'].items():
        valid_accounts[platform] = []
        
        for account in data.get('accounts', []):
            if (account.get('username') and 
                account.get('username') != 'ЗАПОЛНИТЬ' and
                account.get('cookies') and 
                account.get('cookies') != 'ЗАПОЛНИТЬ'):
                
                valid_accounts[platform].append(account)
    
    return valid_accounts

def upload_to_tiktok(video_path, account, title):
    """Upload to TikTok using yt-dlp"""
    try:
        # Prepare cookies file
        cookies_file = f"/tmp/cookies_tiktok_{account['id']}.txt"
        with open(cookies_file, 'w') as f:
            f.write(account['cookies'])
        
        # Upload command
        cmd = [
            'yt-dlp',
            '--cookies', cookies_file,
            '--add-metadata',
            '-o', f"%(title)s.%(ext)s",
            '--postprocessor-args', f'title:{title}',
            f'file://{video_path}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up
        os.remove(cookies_file)
        
        return {
            'platform': 'tiktok',
            'account_id': account['id'],
            'status': 'success' if result.returncode == 0 else 'failed',
            'error': result.stderr if result.returncode != 0 else None,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"TikTok upload error: {str(e)}")
        return {
            'platform': 'tiktok',
            'account_id': account['id'],
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def upload_to_instagram(video_path, account, title):
    """Upload to Instagram using instagrapi"""
    try:
        from instagrapi import Client
        
        cl = Client()
        
        # Load cookies if available
        if account.get('cookies'):
            # Parse cookies and set them
            cl.set_cookies(json.loads(account['cookies']))
        else:
            # Login with username/password
            cl.login(account['username'], account['password'])
        
        # Upload video
        media = cl.video_upload(
            video_path,
            caption=title,
            thumbnail=None
        )
        
        return {
            'platform': 'instagram',
            'account_id': account['id'],
            'status': 'success',
            'media_id': media.pk,
            'url': f"https://instagram.com/p/{media.code}/",
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Instagram upload error: {str(e)}")
        return {
            'platform': 'instagram',
            'account_id': account['id'],
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def upload_to_youtube_shorts(video_path, account, title):
    """Upload to YouTube Shorts using youtube-upload"""
    try:
        # Prepare credentials
        client_secrets = f"/tmp/client_secrets_{account['id']}.json"
        credentials = {
            "installed": {
                "client_id": account.get('client_id'),
                "client_secret": account.get('client_secret'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token"
            }
        }
        
        with open(client_secrets, 'w') as f:
            json.dump(credentials, f)
        
        # Upload command
        cmd = [
            'youtube-upload',
            '--title', title,
            '--description', f'{title} #shorts',
            '--category', 'People & Blogs',
            '--tags', 'shorts,motivation,viral',
            '--default-language', 'en',
            '--client-secrets', client_secrets,
            '--credentials-file', f"/tmp/youtube_creds_{account['id']}.json",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Extract video ID from output
        video_id = None
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'Video ID' in line:
                    video_id = line.split(':')[1].strip()
        
        # Clean up
        os.remove(client_secrets)
        
        return {
            'platform': 'youtube',
            'account_id': account['id'],
            'status': 'success' if result.returncode == 0 else 'failed',
            'video_id': video_id,
            'url': f"https://youtube.com/shorts/{video_id}" if video_id else None,
            'error': result.stderr if result.returncode != 0 else None,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"YouTube upload error: {str(e)}")
        return {
            'platform': 'youtube',
            'account_id': account['id'],
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def upload_to_facebook(video_path, account, title):
    """Upload to Facebook using Graph API"""
    try:
        # Facebook requires page access token
        access_token = account.get('access_token')
        page_id = account.get('page_id')
        
        if not access_token or not page_id:
            raise Exception("Facebook requires access_token and page_id")
        
        # Upload video
        url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
        
        with open(video_path, 'rb') as video_file:
            files = {'source': video_file}
            data = {
                'description': title,
                'access_token': access_token
            }
            
            response = requests.post(url, files=files, data=data)
            result = response.json()
        
        if 'id' in result:
            return {
                'platform': 'facebook',
                'account_id': account['id'],
                'status': 'success',
                'video_id': result['id'],
                'url': f"https://facebook.com/{result['id']}",
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'platform': 'facebook',
                'account_id': account['id'],
                'status': 'failed',
                'error': result.get('error', {}).get('message', 'Unknown error'),
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logging.error(f"Facebook upload error: {str(e)}")
        return {
            'platform': 'facebook',
            'account_id': account['id'],
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def upload_to_x(video_path, account, title):
    """Upload to X (Twitter) using API v2"""
    try:
        import tweepy
        
        # Initialize client
        client = tweepy.Client(
            bearer_token=account.get('bearer_token'),
            consumer_key=account.get('api_key'),
            consumer_secret=account.get('api_secret'),
            access_token=account.get('access_token'),
            access_token_secret=account.get('access_token_secret')
        )
        
        # Upload media first
        auth = tweepy.OAuth1UserHandler(
            account.get('api_key'),
            account.get('api_secret'),
            account.get('access_token'),
            account.get('access_token_secret')
        )
        api = tweepy.API(auth)
        
        media = api.media_upload(video_path)
        
        # Create tweet with video
        tweet = client.create_tweet(
            text=title[:280],  # Twitter limit
            media_ids=[media.media_id]
        )
        
        return {
            'platform': 'x',
            'account_id': account['id'],
            'status': 'success',
            'tweet_id': tweet.data['id'],
            'url': f"https://x.com/i/status/{tweet.data['id']}",
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"X upload error: {str(e)}")
        return {
            'platform': 'x',
            'account_id': account['id'],
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def upload_to_platform(video_path, platform, account, title):
    """Route to appropriate upload function"""
    
    upload_functions = {
        'tiktok': upload_to_tiktok,
        'instagram': upload_to_instagram,
        'youtube': upload_to_youtube_shorts,
        'facebook': upload_to_facebook,
        'x': upload_to_x
    }
    
    if platform in upload_functions:
        return upload_functions[platform](video_path, account, title)
    else:
        return {
            'platform': platform,
            'account_id': account['id'],
            'status': 'failed',
            'error': f'Platform {platform} not supported',
            'timestamp': datetime.now().isoformat()
        }

@app.route('/health', methods=['GET'])
def health():
    valid_accounts = validate_accounts()
    
    return jsonify({
        'status': 'ok',
        'service': 'shorts-publisher',
        'configured_accounts': {
            platform: len(accounts) 
            for platform, accounts in valid_accounts.items()
        }
    })

@app.route('/publish-shorts', methods=['POST'])
def publish_shorts():
    """Publish shorts to multiple platforms and accounts"""
    try:
        data = request.json
        clips = data.get('clips', [])
        titles = data.get('titles', [])
        platforms = data.get('platforms', ['tiktok', 'instagram', 'youtube', 'facebook', 'x'])
        
        if not clips:
            return jsonify({'error': 'No clips provided'}), 400
        
        # Validate accounts
        valid_accounts = validate_accounts()
        
        # Check if we have any valid accounts
        total_valid = sum(len(accounts) for accounts in valid_accounts.values())
        if total_valid == 0:
            return jsonify({
                'error': 'No valid accounts configured',
                'message': 'Please configure accounts in accounts-config.json'
            }), 400
        
        results = []
        
        # Process each clip
        for clip_index, clip in enumerate(clips):
            clip_path = clip if isinstance(clip, str) else clip.get('path')
            
            if not clip_path or not os.path.exists(clip_path):
                logging.error(f"Clip not found: {clip_path}")
                continue
            
            clip_results = {
                'clip': clip_path,
                'uploads': []
            }
            
            # Upload to each platform
            for platform in platforms:
                if platform not in valid_accounts:
                    continue
                
                platform_accounts = valid_accounts[platform]
                if not platform_accounts:
                    continue
                
                # Distribute titles for A/B testing
                for account_index, account in enumerate(platform_accounts):
                    title_index = (clip_index + account_index) % len(titles) if titles else 0
                    title = titles[title_index] if titles else f"Video #{clip_index + 1}"
                    
                    # Add delay between uploads to avoid rate limiting
                    if len(clip_results['uploads']) > 0:
                        time.sleep(random.uniform(10, 20))
                    
                    # Upload video
                    upload_result = upload_to_platform(
                        clip_path,
                        platform,
                        account,
                        title
                    )
                    
                    clip_results['uploads'].append(upload_result)
            
            results.append(clip_results)
        
        # Summary statistics
        total_uploads = sum(len(r['uploads']) for r in results)
        successful_uploads = sum(
            1 for r in results 
            for u in r['uploads'] 
            if u['status'] == 'success'
        )
        
        return jsonify({
            'status': 'success',
            'results': results,
            'summary': {
                'total_clips': len(clips),
                'total_uploads': total_uploads,
                'successful_uploads': successful_uploads,
                'success_rate': f"{(successful_uploads/total_uploads*100):.1f}%" if total_uploads > 0 else "0%"
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Error in publish_shorts: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3004, threaded=True)
