"""
Model Evaluation Report Generator
====================================
Reads the saved metrics from all 4 trained models and prints a clean,
organized summary - also saves it as a Markdown file you can use
directly as (or paste into) your Model Evaluation Report deliverable.

Usage:
    python -m app.ml.generate_evaluation_report
"""
import json
import os

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")


def load_metrics(filename):
    path = os.path.join(SAVED_MODELS_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def format_3class_section(title, description, metrics):
    lines = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  {title}")
    lines.append(f"{'=' * 60}")
    lines.append(f"  {description}\n")
    if metrics is None:
        lines.append("  ⚠ No saved results found. Run the training script first.\n")
        return lines
    lines.append(f"  Accuracy:            {metrics['accuracy']*100:.1f}%")
    lines.append(f"  Precision (macro):   {metrics['precision_macro']*100:.1f}%")
    lines.append(f"  Recall (macro):      {metrics['recall_macro']*100:.1f}%")
    lines.append(f"  F1 Score (macro):    {metrics['f1_macro']*100:.1f}%")
    lines.append(f"  Best Params:         {metrics.get('best_params', 'N/A')}")
    lines.append(f"  Train / Test Size:   {metrics['train_size']} / {metrics['test_size']}")
    cm = metrics["confusion_matrix"]
    names = metrics["label_names"]
    lines.append(f"\n  Confusion Matrix (rows=actual, cols=predicted):")
    header = "                " + "".join(f"{n[:10]:>12}" for n in names)
    lines.append(header)
    for i, row in enumerate(cm):
        row_str = "".join(f"{v:>12}" for v in row)
        lines.append(f"    {names[i][:10]:<12}{row_str}")
    return lines


def format_classification_section(title, description, metrics):
    lines = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  {title}")
    lines.append(f"{'=' * 60}")
    lines.append(f"  {description}\n")
    if metrics is None:
        lines.append("  ⚠ No saved results found. Run the training script first.\n")
        return lines
    lines.append(f"  Accuracy:            {metrics['accuracy']*100:.1f}%")
    lines.append(f"  Precision:           {metrics['precision']*100:.1f}%")
    lines.append(f"  Recall:              {metrics['recall']*100:.1f}%")
    lines.append(f"  ROC-AUC:             {metrics['roc_auc']:.3f}")
    lines.append(f"  Decision Threshold:  {metrics['decision_threshold']}")
    lines.append(f"  Train / Test Size:   {metrics['train_size']} / {metrics['test_size']}")
    cm = metrics["confusion_matrix"]
    lines.append(f"\n  Confusion Matrix:")
    lines.append(f"                   Predicted: No    Predicted: Yes")
    lines.append(f"    Actual: No      {cm[0][0]:<15} {cm[0][1]}")
    lines.append(f"    Actual: Yes     {cm[1][0]:<15} {cm[1][1]}")
    return lines


def format_regression_section(title, description, metrics):
    lines = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  {title}")
    lines.append(f"{'=' * 60}")
    lines.append(f"  {description}\n")
    if metrics is None:
        lines.append("  ⚠ No saved results found. Run the training script first.\n")
        return lines
    for target in ["learning_speed", "skill_growth"]:
        m = metrics[target]
        label = target.replace("_", " ").title()
        lines.append(f"  {label}:")
        lines.append(f"    MAE (avg error):   {m['mae']:.4f}")
        lines.append(f"    R² (variance explained): {m['r2']:.4f}")
        lines.append("")
    lines.append(f"  Train / Test Size:   {metrics['train_size']} / {metrics['test_size']}")
    return lines


def main():
    all_lines = []
    all_lines.append("#" * 60)
    all_lines.append("  EZITECH AI-005: MODEL EVALUATION REPORT")
    all_lines.append("  Internship Performance Prediction & Risk Analytics")
    all_lines.append("#" * 60)

    dropout = load_metrics("dropout_risk_metrics.json")
    all_lines += format_classification_section(
        "MODEL 1: DROPOUT RISK  (XGBoost Classifier)",
        "Predicts whether an intern is likely to drop out of the internship.",
        dropout
    )

    performance = load_metrics("performance_trend_metrics.json")
    all_lines += format_3class_section(
        "MODEL 2: PERFORMANCE TREND  (XGBoost Classifier, 3-class)",
        "Predicts an intern's current delivery trend tier: declining,\n"
        "  stable, or improving - based on full-history behavioral signals\n"
        "  (commits, review scores, mentor ratings, communication) that are\n"
        "  independent of the columns used to build the label.",
        performance
    )

    success = load_metrics("success_probability_metrics.json")
    all_lines += format_classification_section(
        "MODEL 3: SUCCESS PROBABILITY  (XGBoost Classifier)",
        "Predicts whether an intern will complete the internship WITH\n"
        "  strong performance (above-median review scores).",
        success
    )

    growth = load_metrics("growth_metrics.json")
    all_lines += format_regression_section(
        "MODEL 4: LEARNING SPEED & SKILL GROWTH  (Linear Regression)",
        "Predicts the RATE of improvement in task completion (Learning Speed)\n"
        "  and code review scores (Skill Growth), based on early-period behavior.",
        growth
    )

    all_lines.append(f"\n{'=' * 60}")
    all_lines.append("  SUMMARY")
    all_lines.append(f"{'=' * 60}")
    all_lines.append("  4 models trained, covering all 8 required predictions:")
    all_lines.append("  (Completion Probability, Project Success Probability, and")
    all_lines.append("   Mentor Workload are derived from these models / direct SQL,")
    all_lines.append("   requiring no additional training - see architecture doc.)")

    output = "\n".join(all_lines)
    print(output)

    # Save as a Markdown file too, ready to paste into your report
    md_path = os.path.join(SAVED_MODELS_DIR, "model_evaluation_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Model Evaluation Report\n")
        f.write("## Ezitech AI-005: Internship Performance Prediction & Risk Analytics\n\n")
        f.write("```\n" + output + "\n```\n")

    print(f"\n\nSaved formatted report to: app/ml/saved_models/model_evaluation_report.md")


if __name__ == "__main__":
    main()