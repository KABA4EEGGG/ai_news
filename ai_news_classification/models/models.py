from typing import List
import numpy as np

import torch.nn.functional as F
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from torch import Tensor
from transformers import AutoTokenizer, AutoModel

tokenizer = AutoTokenizer.from_pretrained('intfloat/multilingual-e5-base')
model = AutoModel.from_pretrained('intfloat/multilingual-e5-base')


def average_pool(last_hidden_states: Tensor,
                 attention_mask: Tensor) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(
        ~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def compute_similarity(input_posts: List[str]) -> List[float]:
    """
    Расчет схожести текстов
    оследний текст сравнивается со всеми остальными

    Args:
        input_posts (List[str]): Входные тексты

    Returns:
        List[float]: Степень схожести текстов с последним
    """
    input_posts = _add_query(input_posts)

    batch_dict = tokenizer(input_posts, max_length=512,
                           padding=True, truncation=True, return_tensors='pt')
    outputs = model(**batch_dict)
    embeddings = average_pool(
        outputs.last_hidden_state, batch_dict['attention_mask'])

    embeddings = F.normalize(embeddings, p=2, dim=1)
    scores = (embeddings[:2] @ embeddings[2:].T) * 100
    scores = np.array(scores.tolist()).flatten()

    return scores


def _add_query(posts: List[str]) -> List[str]:
    for indx, value in enumerate(posts):
        posts[indx] = 'query' + value

    return posts


def predict_zero_shot(text, label_texts, label='entailment', normalize=True):
    model_checkpoint = 'cointegrated/rubert-base-cased-nli-threeway'
    tokenizer = AutoTokenizer.from_pretrained(model_checkpoint)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_checkpoint)
    if torch.cuda.is_available():
        model.cuda()
    tokens = tokenizer([text] * len(label_texts), label_texts,
                       truncation=True, return_tensors='pt', padding=True)
    with torch.inference_mode():
        result = torch.softmax(model(**tokens.to(model.device)).logits, -1)
    proba = result[:, model.config.label2id[label]].cpu().numpy()
    if normalize:
        proba /= sum(proba)
    return proba
