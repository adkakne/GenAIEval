
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
import os
from typing import Dict, Optional, Union
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLanguageModel

import sys
sys.path.append('/home/akakne/miniforge3/envs/recsys/bin')

def format_ragas_metric_name(name: str):
    return f"{name} (ragas)"

class RagasMetric:
    """This metric checks if the output is more than 3 letters."""
    def __init__(
        self,
        threshold: float = 0.3,
        model: Optional[Union[str, BaseLanguageModel]] = None,
        embeddings: Optional[Embeddings] = None,
        metrics: Optional[list[str]] = None,
    ):
        self.threshold = threshold
        self.model = model
        self.embeddings = embeddings
        self.metrics = metrics
        self.validated_list = [
            "answer_correctness",
            "answer_relevancy",
            "answer_similarity",
            "context_precision",
            "context_recall",
            "faithfulness",
            "context_utilization",
            # "reference_free_rubrics_score",
        ]
    async def a_measure(self, test_case: Dict):
        return self.measure(test_case)
    def measure(self, test_case: Dict):
        # sends to server
        try:
            from ragas import evaluate
            from ragas.metrics import (
                answer_correctness,
                answer_relevancy,
                answer_similarity,
                context_precision,
                context_recall,
                context_utilization,
                faithfulness,
                # reference_free_rubrics_score,
            )
        except ModuleNotFoundError:
            raise ModuleNotFoundError("Please install ragas to use this metric. `pip install ragas`.")
        try:
            from datasets import Dataset
        except ModuleNotFoundError:
            raise ModuleNotFoundError("Please install dataset")
        self.metrics_instance = {
            "answer_correctness": answer_correctness,
            "answer_relevancy": answer_relevancy,
            "answer_similarity": answer_similarity,
            "context_precision": context_precision,
            "context_recall": context_recall,
            "faithfulness": faithfulness,
            "context_utilization": context_utilization,
            # "reference_free_rubrics_score": reference_free_rubrics_score,
        }
        # Set LLM model
        openai_key = os.getenv("OPENAI_API_KEY", None)
        if openai_key is not None:
            print("OPENAI_API_KEY is provided, ragas initializes the model by OpenAI.")
            self.model = None
        if isinstance(self.model, str):
            print("Loading a HuggingFace Endpoint")
            chat_model = HuggingFaceEndpoint(
                endpoint_url=self.model,
                timeout=600,
            )
        else:
            print("Accepting user-initialized model as we could not detect OpenAI key or HuggingFace Endpoint URL.")
            chat_model = self.model
        # Create a dataset from the test case
        # Convert the Dict to a format compatible with Dataset
        if self.metrics is not None:
            tmp_metrics = []
            # check supported list
            for metric in self.metrics:
                if metric not in self.validated_list:
                    raise ValueError(
                        "metric should be in supported list {}. ".format(self.validated_list)
                        + "ClientResponseError raised with LangchainLLM "
                        + "when context_precision, context_recall ran. "
                        + "Here are the related issues described in ragas "
                        "https://github.com/explodinggradients/ragas/issues/934, "
                        + "https://github.com/explodinggradients/ragas/issues/664."
                    )
                else:
                    if metric == "answer_relevancy" and self.embeddings is None:
                        raise ValueError("answer_relevancy metric need provide embeddings model.")
                    tmp_metrics.append(self.metrics_instance[metric])
            self.metrics = tmp_metrics
        else:
            self.metrics = [
                answer_relevancy,
                faithfulness,
                answer_correctness,
                answer_similarity,
                context_precision,
                context_recall,
            ]
        # Find necessary input fields using the given metrics
        _required_columns = set()
        for metric in self.metrics:
            for column in list(metric._required_columns.values())[0]:
                _required_columns.add(column)
        column2field = {
            "user_input" : "question",
            "response" : "answer",
            "reference" : "ground_truth",
            "retrieved_contexts" : "contexts"
        }
        _required_fields = [column2field[column] for column in _required_columns]
        data = {field : test_case[field] for field in _required_fields}
        dataset = Dataset.from_dict(data)

        # evaluate
        self.score = evaluate(
            dataset,
            metrics=self.metrics,
            llm=chat_model,
            embeddings=self.embeddings,
        )
        return self.score
    def is_successful(self):
        return self.success
    @property
    def __name__(self):
        return "RAGAS"
