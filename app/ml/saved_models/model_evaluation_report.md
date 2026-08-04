# Model Evaluation Report
## Ezitech AI-005: Internship Performance Prediction & Risk Analytics

```
############################################################
  EZITECH AI-005: MODEL EVALUATION REPORT
  Internship Performance Prediction & Risk Analytics
############################################################

============================================================
  MODEL 1: DROPOUT RISK  (XGBoost Classifier)
============================================================
  Predicts whether an intern is likely to drop out of the internship.

  Accuracy:            85.1%
  Precision:           75.0%
  Recall:              60.0%
  ROC-AUC:             0.842
  Decision Threshold:  0.45
  Train / Test Size:   481 / 121

  Confusion Matrix:
                   Predicted: No    Predicted: Yes
    Actual: No      85              6
    Actual: Yes     12              18

============================================================
  MODEL 2: PERFORMANCE TREND  (XGBoost Classifier, 3-class)
============================================================
  Predicts an intern's current delivery trend tier: declining,
  stable, or improving - based on full-history behavioral signals
  (commits, review scores, mentor ratings, communication) that are
  independent of the columns used to build the label.

  Accuracy:            83.4%
  Precision (macro):   83.5%
  Recall (macro):      83.4%
  F1 Score (macro):    83.4%
  Best Params:         {'learning_rate': 0.05, 'max_depth': 3, 'n_estimators': 100}
  Train / Test Size:   600 / 151

  Confusion Matrix (rows=actual, cols=predicted):
                   declining      stable   improving
    declining             39           9           2
    stable                 7          40           3
    improving              0           4          47

============================================================
  MODEL 3: SUCCESS PROBABILITY  (XGBoost Classifier)
============================================================
  Predicts whether an intern will complete the internship WITH
  strong performance (above-median review scores).

  Accuracy:            90.5%
  Precision:           92.9%
  Recall:              81.2%
  ROC-AUC:             0.947
  Decision Threshold:  0.6
  Train / Test Size:   508 / 127

  Confusion Matrix:
                   Predicted: No    Predicted: Yes
    Actual: No      76              3
    Actual: Yes     9               39

============================================================
  MODEL 4: LEARNING SPEED & SKILL GROWTH  (Linear Regression)
============================================================
  Predicts the RATE of improvement in task completion (Learning Speed)
  and code review scores (Skill Growth), based on early-period behavior.

  Learning Speed:
    MAE (avg error):   0.1489
    R² (variance explained): 0.5941

  Skill Growth:
    MAE (avg error):   0.6440
    R² (variance explained): 0.0231

  Train / Test Size:   640 / 160

============================================================
  SUMMARY
============================================================
  4 models trained, covering all 8 required predictions:
  (Completion Probability, Project Success Probability, and
   Mentor Workload are derived from these models / direct SQL,
   requiring no additional training - see architecture doc.)
```
