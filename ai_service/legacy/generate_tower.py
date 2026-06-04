import asyncio
import os
import sys
import json
from quest_generator import generate_single_quest, sync_to_backend

# Add project root to sys.path
sys.path.append('d:\\Capstone2---C2SE.07\\backend')

# Subject IDs mapping
SUBJECT_MAP = {
    "Toan hoc": 22,
    "Vat ly": 21,
    "Hoa hoc": 24,
    "Sinh hoc": 25,
    "Lich su": 26,
    "Dia ly": 27,
    "Tieng Anh": 28
}

async def build_complete_tower(grade_level: int):
    """Generates a 10-floor tower for a specific grade using AI."""
    print(f"\n--- Constructing AI Tower for GRADE {grade_level} ---", flush=True)
    
    for floor in range(1, 11):
        subject_name = list(SUBJECT_MAP.keys())[(floor - 1) % len(SUBJECT_MAP)]
        subject_id = SUBJECT_MAP[subject_name]
        
        print(f"  [Floor {floor}/10] Subject: {subject_name}...", flush=True)
        
        # Create 3 variants per floor
        for variant in range(3):
            quest = await generate_single_quest(grade_level, floor, subject_name)
            if quest:
                success = await sync_to_backend(quest, subject_id)
                if success:
                    print(f"    - V{variant+1}: Success.")
                else:
                    print(f"    - V{variant+1}: Backend Sync Failed.")
            else:
                print(f"    - V{variant+1}: AI Generation Failed.")

async def main():
    print("--- STARTING AI TOWER GENERATION CAMPAIGN ---", flush=True)
    
    for grade in [10, 11, 12]:
        await build_complete_tower(grade)
    
    print("\n--- ALL TOWERS COMPLETED BY AI ---")

if __name__ == "__main__":
    asyncio.run(main())
