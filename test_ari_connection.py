"""
Quick test script to verify ARI connection
"""
import asyncio
import aiohttp

# Configuration
ARI_URL = "http://localhost:8088/ari"
ARI_USERNAME = "aiagent"
ARI_PASSWORD = "strongpassword"

async def test_connection():
    """Test ARI connection"""
    print("="*60)
    print("Testing Asterisk ARI Connection")
    print("="*60)
    
    auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
    
    try:
        async with aiohttp.ClientSession(auth=auth) as session:
            # Test 1: Check if ARI is accessible
            print("\n[Test 1] Checking ARI API endpoint...")
            url = f"{ARI_URL}/api-docs/resources.json"
            async with session.get(url) as resp:
                if resp.status == 200:
                    print("✓ ARI API is accessible")
                    data = await resp.json()
                    print(f"  API version: {data.get('apiVersion', 'Unknown')}")
                else:
                    print(f"✗ Failed to access ARI: HTTP {resp.status}")
                    return False
            
            # Test 2: Check applications
            print("\n[Test 2] Checking Stasis applications...")
            url = f"{ARI_URL}/applications"
            async with session.get(url) as resp:
                if resp.status == 200:
                    apps = await resp.json()
                    print(f"✓ Found {len(apps)} application(s)")
                    for app in apps:
                        print(f"  - {app.get('name', 'Unknown')}")
                else:
                    print(f"✗ Failed to list applications: HTTP {resp.status}")
            
            # Test 3: Check channels
            print("\n[Test 3] Checking active channels...")
            url = f"{ARI_URL}/channels"
            async with session.get(url) as resp:
                if resp.status == 200:
                    channels = await resp.json()
                    print(f"✓ Found {len(channels)} active channel(s)")
                else:
                    print(f"✗ Failed to list channels: HTTP {resp.status}")
            
            print("\n" + "="*60)
            print("✓ All tests passed! ARI connection is working.")
            print("="*60)
            print("\nYou can now run: python3.10 simple_ari_integration.py")
            return True
            
    except aiohttp.ClientConnectorError as e:
        print(f"\n✗ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if Asterisk is running: sudo systemctl status asterisk")
        print("2. Check if HTTP is enabled: /etc/asterisk/http.conf")
        print("3. Check if ARI is enabled: /etc/asterisk/ari.conf")
        print("4. Restart Asterisk: sudo systemctl restart asterisk")
        return False
    except aiohttp.ClientResponseError as e:
        print(f"\n✗ HTTP Error: {e}")
        print("\nCheck your credentials in /etc/asterisk/ari.conf")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
