#!/usr/bin/env python3
"""
Test script to verify that LogoConfig handles None values properly.
This tests the fix for the validation error where margin=None was causing crashes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_generator.generator import LogoConfig

def test_logo_config_with_none_values():
    """Test that LogoConfig can handle None values for optional fields."""
    
    print("Testing LogoConfig with None values...")
    
    # Test 1: All fields with explicit values
    try:
        logo1 = LogoConfig(
            url="https://example.com/logo.png",
            position="bottom-right",
            opacity=0.6,
            show_in_all_scenes=True,
            cta_screen=True,
            size=(100, 50),
            margin=30
        )
        print("✅ Test 1 passed: All fields with explicit values")
        print(f"   margin: {logo1.margin}, size: {logo1.size}")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False
    
    # Test 2: None values for optional fields (should use defaults)
    try:
        logo2 = LogoConfig(
            url="https://example.com/logo.png",
            position="bottom-right",
            opacity=0.6,
            show_in_all_scenes=True,
            cta_screen=True,
            size=None,  # Should be None
            margin=None  # Should default to 20
        )
        print("✅ Test 2 passed: None values for optional fields")
        print(f"   margin: {logo2.margin} (should be 20), size: {logo2.size} (should be None)")
        
        # Verify defaults are applied
        if logo2.margin == 20 and logo2.size is None:
            print("   ✅ Defaults applied correctly")
        else:
            print(f"   ❌ Defaults not applied correctly: margin={logo2.margin}, size={logo2.size}")
            return False
            
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False
    
    # Test 3: Minimal configuration (only required fields)
    try:
        logo3 = LogoConfig(url="https://example.com/logo.png")
        print("✅ Test 3 passed: Minimal configuration")
        print(f"   margin: {logo3.margin} (should be 20), size: {logo3.size} (should be None)")
        
        # Verify defaults are applied
        if logo3.margin == 20 and logo3.size is None:
            print("   ✅ Defaults applied correctly")
        else:
            print(f"   ❌ Defaults not applied correctly: margin={logo3.margin}, size={logo3.size}")
            return False
            
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return False
    
    # Test 4: Simulate the actual payload from the error
    try:
        logo4 = LogoConfig(
            url="https://pub-b3d68bfabb5742dabcd0275d1b282f2a.r2.dev/f83ba57b-4730-4e67-b549-eac4ac857cda.png",
            position="bottom-right",
            opacity=0.6,
            show_in_all_scenes=True,
            cta_screen=True,
            size=None,
            margin=None
        )
        print("✅ Test 4 passed: Simulated actual payload")
        print(f"   margin: {logo4.margin}, size: {logo4.size}")
        
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        return False
    
    print("\n🎉 All tests passed! LogoConfig now handles None values properly.")
    return True

if __name__ == "__main__":
    success = test_logo_config_with_none_values()
    if not success:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
    else:
        print("\n✅ LogoConfig validation fix is working correctly!") 