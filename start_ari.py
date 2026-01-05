"""
Asterisk ARI Application Startup Script
Starts the ARI bridge to handle incoming calls
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.telephony.ari_bridge import get_ari_bridge
from app.logger import logger


async def main():
    """
    Main entry point for ARI application
    """
    logger.info("="*60)
    logger.info("ASTERISK ARI BRIDGE - STARTING")
    logger.info("="*60)
    
    ari_bridge = get_ari_bridge()
    
    try:
        # Connect to Asterisk ARI
        await ari_bridge.connect()
        
        logger.info("✓ ARI Bridge connected successfully")
        logger.info("Listening for incoming calls...")
        logger.info("Press CTRL+C to stop")
        logger.info("="*60)
        
        # Handle events
        await ari_bridge.handle_events()
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down ARI bridge...")
    
    except Exception as e:
        logger.error(f"Fatal error in ARI bridge: {e}")
    
    finally:
        await ari_bridge.disconnect()
        logger.info("✓ ARI Bridge stopped")


if __name__ == "__main__":
    asyncio.run(main())
