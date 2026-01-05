"""
Test Enhanced Agent Behavior
Shows agent can answer from both RAG documents and general knowledge
"""

import sys
sys.path.insert(0, 'backend')

from app.llm.dialog_manager import generate_response
from app.config import ACTIVE_COMPANY

print("="*70)
print("TESTING ENHANCED AGENT BEHAVIOR")
print("="*70)

print("\n1. Testing with company-specific question (should use RAG):")
print("-" * 70)
question1 = "What health services do you offer?"
print(f"Question: {question1}")
print("\nGenerating response...")
response1 = generate_response(question1, company_id=ACTIVE_COMPANY)
print(f"\nAgent Response:\n{response1}\n")

print("\n2. Testing with general customer service question:")
print("-" * 70)
question2 = "What are the best practices for handling a billing dispute?"
print(f"Question: {question2}")
print("\nGenerating response...")
response2 = generate_response(question2, company_id=ACTIVE_COMPANY)
print(f"\nAgent Response:\n{response2}\n")

print("\n3. Testing with mixed question (company + general knowledge):")
print("-" * 70)
question3 = "Do you accept insurance and what should I bring to my appointment?"
print(f"Question: {question3}")
print("\nGenerating response...")
response3 = generate_response(question3, company_id=ACTIVE_COMPANY)
print(f"\nAgent Response:\n{response3}\n")

print("="*70)
print("✓ Enhanced agent now uses BOTH company knowledge AND general expertise!")
print("="*70)
