#!/usr/bin/env python3
"""
PhotoCleaner Feedback Analyzer

Analyzes collected feedback JSON files and generates insights.
Usage: python analyze_feedback.py [feedback_directory]
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any


def load_feedback_files(directory: Path) -> List[Dict[str, Any]]:
    """Load all feedback JSON files from directory."""
    feedback_files = list(directory.glob("feedback_*.json"))
    
    if not feedback_files:
        print(f"❌ No feedback files found in {directory}")
        sys.exit(1)
    
    feedbacks = []
    for file in feedback_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                feedbacks.append(data)
        except Exception as e:
            print(f"⚠️  Error loading {file.name}: {e}")
    
    print(f"✅ Loaded {len(feedbacks)} feedback responses\n")
    return feedbacks


def analyze_ratings(feedbacks: List[Dict[str, Any]]) -> None:
    """Analyze all rating-based questions."""
    print("=" * 60)
    print("📊 RATING ANALYSIS")
    print("=" * 60)
    
    rating_fields = {
        "trust": "Auto-Select Trust (1-5)",
        "eye_quality": "Eye Quality Detection (1-5)",
        "sharpness": "Sharpness Detection (1-5)",
        "lighting": "Lighting & Exposure (1-5)",
        "nps": "Net Promoter Score (1-10)",
        "overall": "Overall Rating (1-5)",
    }
    
    for field, label in rating_fields.items():
        values = [int(fb.get(field, 0)) for fb in feedbacks if fb.get(field)]
        
        if not values:
            continue
        
        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)
        
        print(f"\n{label}:")
        print(f"  Average: {avg:.2f}")
        print(f"  Range: {min_val} - {max_val}")
        print(f"  Responses: {len(values)}")
        
        # Distribution
        distribution = Counter(values)
        print(f"  Distribution:")
        for rating in sorted(distribution.keys()):
            count = distribution[rating]
            percentage = (count / len(values)) * 100
            bar = "█" * int(percentage / 5)
            print(f"    {rating}: {bar} {percentage:.1f}% ({count})")


def analyze_accuracy(feedbacks: List[Dict[str, Any]]) -> None:
    """Analyze auto-select accuracy percentage."""
    print("\n" + "=" * 60)
    print("🎯 AUTO-SELECT ACCURACY")
    print("=" * 60)
    
    accuracies = [int(fb.get("accuracy", 0)) for fb in feedbacks if fb.get("accuracy")]
    
    if not accuracies:
        print("No accuracy data available")
        return
    
    avg_accuracy = sum(accuracies) / len(accuracies)
    min_acc = min(accuracies)
    max_acc = max(accuracies)
    
    print(f"\nAverage Accuracy: {avg_accuracy:.1f}%")
    print(f"Range: {min_acc}% - {max_acc}%")
    print(f"Responses: {len(accuracies)}")
    
    # Accuracy buckets
    buckets = {
        "0-25%": 0,
        "26-50%": 0,
        "51-75%": 0,
        "76-90%": 0,
        "91-100%": 0,
    }
    
    for acc in accuracies:
        if acc <= 25:
            buckets["0-25%"] += 1
        elif acc <= 50:
            buckets["26-50%"] += 1
        elif acc <= 75:
            buckets["51-75%"] += 1
        elif acc <= 90:
            buckets["76-90%"] += 1
        else:
            buckets["91-100%"] += 1
    
    print("\nAccuracy Distribution:")
    for bucket, count in buckets.items():
        percentage = (count / len(accuracies)) * 100
        bar = "█" * int(percentage / 5)
        print(f"  {bucket}: {bar} {percentage:.1f}% ({count})")


def analyze_image_types(feedbacks: List[Dict[str, Any]]) -> None:
    """Analyze which image types were tested."""
    print("\n" + "=" * 60)
    print("📸 IMAGE TYPES TESTED")
    print("=" * 60)
    
    image_types = []
    for fb in feedbacks:
        types = fb.get("image_types", [])
        if isinstance(types, str):
            types = [types]
        image_types.extend(types)
    
    type_counter = Counter(image_types)
    
    print(f"\nTotal responses: {len(feedbacks)}")
    print(f"\nImage types distribution:")
    for img_type, count in type_counter.most_common():
        percentage = (count / len(feedbacks)) * 100
        print(f"  {img_type}: {count} ({percentage:.1f}%)")


def analyze_performance(feedbacks: List[Dict[str, Any]]) -> None:
    """Analyze performance metrics."""
    print("\n" + "=" * 60)
    print("⚡ PERFORMANCE FEEDBACK")
    print("=" * 60)
    
    speed_ratings = [fb.get("speed", "") for fb in feedbacks if fb.get("speed")]
    speed_counter = Counter(speed_ratings)
    
    print(f"\nSpeed Ratings:")
    for speed, count in speed_counter.most_common():
        percentage = (count / len(speed_ratings)) * 100
        print(f"  {speed}: {count} ({percentage:.1f}%)")
    
    # Crashes
    crashes = [fb.get("crashes", "").strip() for fb in feedbacks if fb.get("crashes", "").strip()]
    
    print(f"\n\nCrashes/Freezes Reported: {len(crashes)}")
    if crashes:
        print("\nCrash Reports:")
        for i, crash in enumerate(crashes, 1):
            print(f"  {i}. {crash[:100]}...")


def analyze_text_feedback(feedbacks: List[Dict[str, Any]]) -> None:
    """Analyze qualitative text feedback."""
    print("\n" + "=" * 60)
    print("💬 QUALITATIVE FEEDBACK")
    print("=" * 60)
    
    text_fields = {
        "likes": "What Users LOVE",
        "dislikes": "What Users DISLIKE",
        "common_errors": "Common Auto-Select Errors",
        "bugs": "Bug Reports",
    }
    
    for field, label in text_fields.items():
        responses = [fb.get(field, "").strip() for fb in feedbacks if fb.get(field, "").strip()]
        
        print(f"\n\n{label} ({len(responses)} responses):")
        print("-" * 60)
        
        for i, response in enumerate(responses, 1):
            # Truncate long responses
            display = response if len(response) <= 200 else response[:200] + "..."
            print(f"\n{i}. {display}")


def analyze_purchase_intent(feedbacks: List[Dict[str, Any]]) -> None:
    """Analyze purchase intent."""
    print("\n" + "=" * 60)
    print("💰 PURCHASE INTENT")
    print("=" * 60)
    
    purchase_intent = [fb.get("would_buy", "") for fb in feedbacks if fb.get("would_buy")]
    intent_counter = Counter(purchase_intent)
    
    print(f"\nWould buy PhotoCleaner PRO (€59/year)?")
    for intent, count in intent_counter.most_common():
        percentage = (count / len(purchase_intent)) * 100
        print(f"  {intent}: {count} ({percentage:.1f}%)")
    
    # Purchase reasons
    reasons = [fb.get("buy_reason", "").strip() for fb in feedbacks if fb.get("buy_reason", "").strip()]
    
    if reasons:
        print(f"\n\nPurchase Reasoning ({len(reasons)} responses):")
        print("-" * 60)
        for i, reason in enumerate(reasons, 1):
            display = reason if len(reason) <= 150 else reason[:150] + "..."
            print(f"\n{i}. {display}")


def calculate_nps(feedbacks: List[Dict[str, Any]]) -> None:
    """Calculate Net Promoter Score."""
    print("\n" + "=" * 60)
    print("📈 NET PROMOTER SCORE (NPS)")
    print("=" * 60)
    
    nps_scores = [int(fb.get("nps", 0)) for fb in feedbacks if fb.get("nps")]
    
    if not nps_scores:
        print("No NPS data available")
        return
    
    promoters = len([s for s in nps_scores if s >= 9])  # 9-10
    passives = len([s for s in nps_scores if 7 <= s <= 8])  # 7-8
    detractors = len([s for s in nps_scores if s <= 6])  # 0-6
    
    total = len(nps_scores)
    nps = ((promoters - detractors) / total) * 100
    
    print(f"\nTotal Responses: {total}")
    print(f"\nPromoters (9-10): {promoters} ({promoters/total*100:.1f}%)")
    print(f"Passives (7-8): {passives} ({passives/total*100:.1f}%)")
    print(f"Detractors (0-6): {detractors} ({detractors/total*100:.1f}%)")
    print(f"\n🎯 Net Promoter Score: {nps:.1f}")
    
    if nps >= 50:
        print("   ✅ EXCELLENT!")
    elif nps >= 30:
        print("   ✅ GREAT!")
    elif nps >= 10:
        print("   👍 GOOD")
    elif nps >= 0:
        print("   ⚠️  NEEDS IMPROVEMENT")
    else:
        print("   ❌ CRITICAL - MAJOR ISSUES")


def generate_summary(feedbacks: List[Dict[str, Any]]) -> None:
    """Generate executive summary."""
    print("\n" + "=" * 60)
    print("📋 EXECUTIVE SUMMARY")
    print("=" * 60)
    
    # Key metrics
    avg_accuracy = sum(int(fb.get("accuracy", 0)) for fb in feedbacks if fb.get("accuracy")) / max(len([fb for fb in feedbacks if fb.get("accuracy")]), 1)
    avg_trust = sum(int(fb.get("trust", 0)) for fb in feedbacks if fb.get("trust")) / max(len([fb for fb in feedbacks if fb.get("trust")]), 1)
    avg_overall = sum(int(fb.get("overall", 0)) for fb in feedbacks if fb.get("overall")) / max(len([fb for fb in feedbacks if fb.get("overall")]), 1)
    
    nps_scores = [int(fb.get("nps", 0)) for fb in feedbacks if fb.get("nps")]
    promoters = len([s for s in nps_scores if s >= 9])
    detractors = len([s for s in nps_scores if s <= 6])
    nps = ((promoters - detractors) / max(len(nps_scores), 1)) * 100
    
    print(f"\n📊 Key Metrics:")
    print(f"  • Total Responses: {len(feedbacks)}")
    print(f"  • Auto-Select Accuracy: {avg_accuracy:.1f}%")
    print(f"  • Trust Level: {avg_trust:.1f}/5")
    print(f"  • Overall Rating: {avg_overall:.1f}/5")
    print(f"  • Net Promoter Score: {nps:.1f}")
    
    # Most common image count
    image_counts = [fb.get("image_count", "") for fb in feedbacks if fb.get("image_count")]
    most_common_count = Counter(image_counts).most_common(1)
    if most_common_count:
        print(f"  • Most Common Test Size: {most_common_count[0][0]}")
    
    print(f"\n🎯 Recommendations:")
    
    if avg_accuracy < 70:
        print("  ⚠️  AUTO-SELECT ACCURACY NEEDS IMPROVEMENT (<70%)")
        print("     → Focus on algorithm refinement (Phase 3 priority)")
    elif avg_accuracy < 85:
        print("  👍 Auto-Select is good but can be better")
        print("     → Continue Phase 3 improvements")
    else:
        print("  ✅ Auto-Select accuracy is excellent!")
    
    if avg_trust < 3.5:
        print("  ⚠️  LOW USER TRUST - Critical Issue")
        print("     → Users don't trust auto-selection")
    elif avg_trust < 4.0:
        print("  👍 Trust is decent, room for improvement")
    else:
        print("  ✅ Users trust the auto-selection!")
    
    if nps < 30:
        print("  ⚠️  NPS is below target - Major improvements needed")
    elif nps < 50:
        print("  👍 NPS is good, aim for >50")
    else:
        print("  ✅ EXCELLENT NPS - Users love it!")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🎨 PhotoCleaner v0.8.2 Feedback Analyzer")
    print("=" * 60 + "\n")
    
    # Determine feedback directory
    if len(sys.argv) > 1:
        feedback_dir = Path(sys.argv[1])
    else:
        # Default to project root / feedback_results
        feedback_dir = Path(__file__).parent.parent / "feedback_results"
    
    if not feedback_dir.exists():
        print(f"❌ Directory not found: {feedback_dir}")
        print(f"\nUsage: python {Path(__file__).name} [feedback_directory]")
        sys.exit(1)
    
    # Load feedback files
    feedbacks = load_feedback_files(feedback_dir)
    
    # Run all analyses
    analyze_ratings(feedbacks)
    analyze_accuracy(feedbacks)
    analyze_image_types(feedbacks)
    analyze_performance(feedbacks)
    calculate_nps(feedbacks)
    analyze_purchase_intent(feedbacks)
    analyze_text_feedback(feedbacks)
    generate_summary(feedbacks)
    
    print("\n" + "=" * 60)
    print("✅ Analysis Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
