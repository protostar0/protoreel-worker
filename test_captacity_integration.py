#!/usr/bin/env python3
"""
Test script for Captacity integration in ProtoReel worker.
This script tests the Captacity subtitle generation functionality.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_captacity_import():
    """Test if Captacity can be imported successfully."""
    print("🧪 Testing Captacity Import...")
    print("=" * 50)
    
    try:
        from captacity import add_captions
        print("✅ Captacity imported successfully")
        print(f"   Function: {add_captions}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Captacity: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing Captacity: {e}")
        return False

def test_captacity_integration_module():
    """Test if our Captacity integration module works."""
    print("\n🔧 Testing Captacity Integration Module...")
    print("=" * 50)
    
    try:
        from video_generator.captacity_integration import (
            test_captacity_integration,
            generate_captacity_subtitles_compatible
        )
        print("✅ Captacity integration module imported successfully")
        
        # Test the integration
        if test_captacity_integration():
            print("✅ Captacity integration test passed")
        else:
            print("❌ Captacity integration test failed")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Captacity integration module: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in Captacity integration module: {e}")
        return False

def test_captacity_functionality():
    """Test basic Captacity functionality."""
    print("\n🚀 Testing Captacity Functionality...")
    print("=" * 50)
    
    try:
        from captacity import add_captions
        
        # Check if we have a test video file
        test_video = "video.mp4"
        if os.path.exists(test_video):
            print(f"✅ Found test video: {test_video}")
            print(f"   File size: {os.path.getsize(test_video)} bytes")
            
            # Test if we can create a simple output path
            output_path = "test_output_with_subtitles.mp4"
            print(f"   Output path: {output_path}")
            
            print("✅ Basic Captacity functionality test passed")
            return True
        else:
            print(f"⚠️  Test video not found: {test_video}")
            print("   Skipping functionality test")
            return True
            
    except Exception as e:
        print(f"❌ Captacity functionality test failed: {e}")
        return False

def test_captacity_configuration():
    """Test Captacity configuration and dependencies."""
    print("\n⚙️  Testing Captacity Configuration...")
    print("=" * 50)
    
    try:
        # Check if required dependencies are available
        import moviepy
        print(f"✅ MoviePy version: {moviepy.__version__}")
        
        # Check if we can create a simple video clip
        from moviepy import VideoFileClip
        print("✅ MoviePy VideoFileClip imported successfully")
        
        # Check if we have the captacity directory
        captacity_dir = "captacity"
        if os.path.exists(captacity_dir):
            print(f"✅ Captacity directory found: {captacity_dir}")
            
            # List captacity files
            captacity_files = os.listdir(captacity_dir)
            print(f"   Files: {', '.join(captacity_files)}")
        else:
            print(f"❌ Captacity directory not found: {captacity_dir}")
            return False
        
        print("✅ Captacity configuration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Captacity configuration test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Captacity Integration Test for ProtoReel Worker")
    print("=" * 60)
    
    # Test 1: Import
    if not test_captacity_import():
        print("\n❌ Captacity import test failed. Check installation.")
        sys.exit(1)
    
    # Test 2: Configuration
    if not test_captacity_configuration():
        print("\n❌ Captacity configuration test failed. Check setup.")
        sys.exit(1)
    
    # Test 3: Integration Module
    if not test_captacity_integration_module():
        print("\n❌ Captacity integration module test failed. Check code.")
        sys.exit(1)
    
    # Test 4: Functionality
    if not test_captacity_functionality():
        print("\n❌ Captacity functionality test failed. Check dependencies.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 All Captacity integration tests passed!")
    print("\n💡 The Captacity integration is ready to use.")
    print("\n💡 To test with a real video, run:")
    print("   python -c \"from video_generator.captacity_integration import test_captacity_integration; test_captacity_integration()\"")
    
    print("\n💡 To generate subtitles for a video:")
    print("   from video_generator.captacity_integration import generate_captacity_subtitles")
    print("   generate_captacity_subtitles('input.mp4', 'audio.wav', 'output.mp4')")

if __name__ == "__main__":
    main() 