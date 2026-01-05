"""
Test script for AI Voice Agent Pipeline
Tests all components: RAG, TTS, and complete voice pipeline
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.rag.vector_store import RAGSystem
from app.tts.coqui_tts import synthesize_speech
from app.pipelines.voice_pipeline import get_pipeline
from app.config import COMPANIES_DIR, ACTIVE_COMPANY
from app.logger import logger

def test_rag_system():
    """Test RAG system initialization and retrieval"""
    print("\n" + "="*60)
    print("TEST 1: RAG System")
    print("="*60)
    
    try:
        # Initialize RAG
        print(f"Initializing RAG for company: {ACTIVE_COMPANY}")
        rag = RAGSystem(COMPANIES_DIR)
        rag.load_company(ACTIVE_COMPANY)
        
        # Test queries
        test_queries = [
            "What are your office hours?",
            "How do I schedule an appointment?",
            "What insurance plans do you accept?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            context = rag.retrieve(query, top_k=2)
            print(f"Retrieved context ({len(context)} chars):")
            print(context[:300] + "..." if len(context) > 300 else context)
        
        print("\n✅ RAG System Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ RAG System Test: FAILED - {e}")
        return False


def test_tts_system():
    """Test Text-to-Speech system"""
    print("\n" + "="*60)
    print("TEST 2: Text-to-Speech")
    print("="*60)
    
    try:
        test_text = "Hello! This is a test of the text to speech system. How can I help you today?"
        
        print(f"Converting text to speech: {test_text}")
        audio_path = synthesize_speech(test_text, output_filename="test_tts_output.wav")
        
        print(f"✅ Audio generated: {audio_path}")
        print(f"   File size: {audio_path.stat().st_size} bytes")
        print(f"   File exists: {audio_path.exists()}")
        
        print("\n✅ TTS System Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TTS System Test: FAILED - {e}")
        return False


def test_text_pipeline():
    """Test complete text-to-audio pipeline"""
    print("\n" + "="*60)
    print("TEST 3: Text-to-Audio Pipeline")
    print("="*60)
    
    try:
        pipeline = get_pipeline(ACTIVE_COMPANY)
        
        test_query = "What insurance plans do you accept?"
        print(f"Processing query: {test_query}")
        
        result = pipeline.process_text_to_audio(test_query)
        
        print(f"\nPipeline Result:")
        print(f"  Success: {result['success']}")
        print(f"  Response: {result['response_text'][:200]}...")
        print(f"  Audio Path: {result['response_audio_path']}")
        print(f"  Stages: {result['stages_completed']}")
        
        if result['success'] and result['response_audio_path']:
            audio_file = Path(result['response_audio_path'])
            print(f"  Audio file size: {audio_file.stat().st_size} bytes")
        
        print("\n✅ Text Pipeline Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Text Pipeline Test: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_companies():
    """Test multi-company support"""
    print("\n" + "="*60)
    print("TEST 4: Multi-Company Support")
    print("="*60)
    
    try:
        from app.rag.kb_loader import KnowledgeBaseLoader
        
        loader = KnowledgeBaseLoader(COMPANIES_DIR)
        companies = loader.get_available_companies()
        
        print(f"Available companies: {companies}")
        
        for company in companies[:2]:  # Test first 2 companies
            print(f"\nTesting company: {company}")
            docs = loader.load_company_knowledge(company)
            print(f"  Documents loaded: {len(docs)}")
            if docs:
                print(f"  Sample content: {docs[0].content[:100]}...")
        
        print("\n✅ Multi-Company Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Multi-Company Test: FAILED - {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("AI VOICE AGENT - SYSTEM TESTS")
    print("🚀"*30)
    
    results = []
    
    # Run tests
    results.append(("RAG System", test_rag_system()))
    results.append(("TTS System", test_tts_system()))
    results.append(("Text Pipeline", test_text_pipeline()))
    results.append(("Multi-Company", test_companies()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check logs above.")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
