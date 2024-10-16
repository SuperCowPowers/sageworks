"""Tests for the Endpoint functionality"""

import pandas as pd

# SageWorks Imports
from sageworks.core.artifacts.endpoint_core import EndpointCore
from sageworks.utils.endpoint_utils import fs_evaluation_data

reg_endpoint = EndpointCore("abalone-regression-end")
class_endpoint = EndpointCore("wine-classification-end")


def test_general_info():
    """Simple test of the Endpoint functionality"""

    # Call the various methods

    # Let's do a check/validation of the Endpoint
    assert reg_endpoint.exists()

    # Creation/Modification Times
    print(reg_endpoint.created())
    print(reg_endpoint.modified())

    # Get the tags associated with this Endpoint
    print(f"Tags: {reg_endpoint.get_tags()}")


def test_regression_auto_inference():
    pred_df = reg_endpoint.auto_inference()
    print(pred_df)


def test_classification_auto_inference():
    pred_df = class_endpoint.auto_inference()
    print(pred_df)


def test_classification_inference_with_subset_of_labels():
    eval_data_df = fs_evaluation_data(class_endpoint)[:50]

    # Subset the rows to only include the first 2 classes
    eval_data_df = eval_data_df[eval_data_df["wine_class"].isin(["TypeA", "TypeB"])]
    pred_df = class_endpoint.inference(eval_data_df)
    print(pred_df)

    # Subset the rows to only include one label
    eval_data_df = eval_data_df[eval_data_df["wine_class"].isin(["TypeA"])]
    pred_df = class_endpoint.inference(eval_data_df)
    print(pred_df)

    # Try only one row
    eval_data_df = eval_data_df.iloc[:1]
    pred_df = class_endpoint.inference(eval_data_df)
    print(pred_df)

    # Try ZERO rows
    eval_data_df = eval_data_df.iloc[:0]
    pred_df = class_endpoint.inference(eval_data_df)
    print(pred_df)


def test_classification_roc_auc():

    # Compute performance metrics for our test predictions
    eval_data_df = fs_evaluation_data(class_endpoint)[:50]
    pred_df = class_endpoint.inference(eval_data_df)

    # Normal test ROCAUC should 1 (or close to 1)
    target_column = "wine_class"
    metrics = class_endpoint.classification_metrics(target_column, pred_df)
    print(metrics)

    # Now switch the prediction probability columns and check the ROCAUC
    temp = pred_df["TypeA_proba"]
    pred_df["TypeA_proba"] = pred_df["TypeB_proba"]
    pred_df["TypeB_proba"] = temp
    metrics = class_endpoint.classification_metrics(target_column, pred_df)
    print(metrics)

    # Okay, now we're going to generate a fake prediction dataframe
    data = {
        "id": [1, 2, 3, 4, 5],
        "target": ["TypeB", "TypeC", "TypeA", "TypeB", "TypeA"],  # True classes
        "prediction": ["TypeA", "TypeA", "TypeB", "TypeC", "TypeC"],  # Wrong predictions for all rows
        "TypeB_proba": [0.33, 0.33, 0.34, 0.33, 0.33],  # Probabilities for class B
        "TypeC_proba": [0.33, 0.33, 0.33, 0.34, 0.34],  # Probabilities for class C
        "TypeA_proba": [0.34, 0.34, 0.33, 0.33, 0.33],  # Probabilities for class A
    }
    pred_df = pd.DataFrame(data)
    metrics = class_endpoint.classification_metrics("target", pred_df)
    print(metrics)


def test_manual_inference():
    eval_data_df = fs_evaluation_data(reg_endpoint)[:50]
    pred_df = reg_endpoint.inference(eval_data_df)
    print(pred_df)


def test_regression_metrics():
    # Compute performance metrics for our test predictions
    target_column = "class_number_of_rings"
    eval_data_df = fs_evaluation_data(reg_endpoint)[:50]
    pred_df = reg_endpoint.inference(eval_data_df)
    metrics = reg_endpoint.regression_metrics(target_column, pred_df)
    print(metrics)

    # Compute residuals for our test predictions
    residuals = reg_endpoint.residuals(target_column, pred_df)
    print(residuals)


def test_classification_metrics():
    eval_data_df = fs_evaluation_data(class_endpoint)[:50]
    pred_df = class_endpoint.inference(eval_data_df)
    print(pred_df)

    # Classification Metrics
    target_column = "wine_class"
    metrics = class_endpoint.classification_metrics(target_column, pred_df)
    print(metrics)

    # Classification Confusion Matrix
    confusion_matrix = class_endpoint.generate_confusion_matrix(target_column, pred_df)
    print(confusion_matrix)

    # What happens if we ask for residuals on a classification endpoint?
    residuals = class_endpoint.residuals(target_column, pred_df)
    print(residuals)


if __name__ == "__main__":

    # Run the tests
    test_general_info()
    test_regression_auto_inference()
    test_classification_auto_inference()
    test_manual_inference()
    test_classification_inference_with_subset_of_labels()
    test_regression_metrics()
    test_classification_metrics()
    test_classification_roc_auc()

    print("All tests passed!")
