"""
Simple server starter script
Run with: python3.10 start.py
"""
import subprocess
import sys
import os

def main():
    print("="*60)
    print("AI VOICE AGENT - SERVER STARTER")
    print("="*60)
    print()
    
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print()
    print("Starting FastAPI server...")
    print("Server will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print()
    print("Press CTRL+C to stop the server")
    print("="*60)
    print()
    
    # Start uvicorn
    try:
        subprocess.run([
            sys.executable,
            "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
