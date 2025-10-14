#!/usr/bin/env python3
"""
Script to scan all challenges and generate metadata JSON for the online testing website
"""

import os
import json
import sys
import re
from pathlib import Path

def extract_challenge_metadata(challenge_dir):
    """Extract metadata from a challenge directory"""
    challenge_py = os.path.join(challenge_dir, 'challenge.py')
    challenge_html = os.path.join(challenge_dir, 'challenge.html')
    
    if not os.path.exists(challenge_py) or not os.path.exists(challenge_html):
        return None
    
    metadata = {
        'id': os.path.basename(challenge_dir),
        'path': challenge_dir,
        'name': '',
        'difficulty': '',
        'description': '',
        'access_tier': 'free'
    }
    
    # Extract difficulty from path
    if '/easy/' in challenge_dir:
        metadata['difficulty'] = 'easy'
    elif '/medium/' in challenge_dir:
        metadata['difficulty'] = 'medium'
    elif '/hard/' in challenge_dir:
        metadata['difficulty'] = 'hard'
    
    # Read challenge.py to extract name
    try:
        with open(challenge_py, 'r') as f:
            content = f.read()
            # Find name in __init__
            name_match = re.search(r'name="([^"]+)"', content)
            if name_match:
                metadata['name'] = name_match.group(1)
            
            # Find access_tier
            tier_match = re.search(r'access_tier="([^"]+)"', content)
            if tier_match:
                metadata['access_tier'] = tier_match.group(1)
    except Exception as e:
        print(f"Error reading {challenge_py}: {e}")
    
    # Read challenge.html to extract description
    try:
        with open(challenge_html, 'r') as f:
            content = f.read()
            # Extract first paragraph as description
            p_match = re.search(r'<p>\s*([^<]+)', content)
            if p_match:
                # Clean up whitespace
                desc = ' '.join(p_match.group(1).split())
                # Truncate if too long
                metadata['description'] = desc[:200] + '...' if len(desc) > 200 else desc
    except Exception as e:
        print(f"Error reading {challenge_html}: {e}")
    
    # Check for starter files
    starter_dir = os.path.join(challenge_dir, 'starter')
    if os.path.exists(starter_dir):
        starter_files = os.listdir(starter_dir)
        metadata['frameworks'] = [f.replace('starter.', '').replace('.py', '') for f in starter_files]
    else:
        metadata['frameworks'] = []
    
    return metadata

def scan_challenges(base_dir='challenges'):
    """Scan all challenges and return metadata"""
    challenges = []
    
    for difficulty in ['easy', 'medium', 'hard']:
        difficulty_dir = os.path.join(base_dir, difficulty)
        if not os.path.exists(difficulty_dir):
            continue
        
        for challenge_name in sorted(os.listdir(difficulty_dir)):
            challenge_dir = os.path.join(difficulty_dir, challenge_name)
            if not os.path.isdir(challenge_dir):
                continue
            
            metadata = extract_challenge_metadata(challenge_dir)
            if metadata:
                challenges.append(metadata)
                print(f"✓ Scanned: {metadata['difficulty']}/{metadata['id']} - {metadata['name']}")
    
    return challenges

def main():
    # Change to workspace directory
    workspace_dir = Path(__file__).parent.parent
    os.chdir(workspace_dir)
    
    print("Scanning challenges...")
    challenges = scan_challenges()
    
    print(f"\nFound {len(challenges)} challenges")
    
    # Save to JSON
    output_file = 'website/challenges.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(challenges, f, indent=2)
    
    print(f"✓ Metadata saved to {output_file}")
    
    # Print statistics
    stats = {}
    for challenge in challenges:
        diff = challenge['difficulty']
        stats[diff] = stats.get(diff, 0) + 1
    
    print("\nChallenge Statistics:")
    for diff in ['easy', 'medium', 'hard']:
        print(f"  {diff.capitalize()}: {stats.get(diff, 0)}")

if __name__ == '__main__':
    main()
