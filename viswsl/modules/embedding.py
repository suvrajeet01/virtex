import functools

import torch
from torch import nn


class WordAndPositionalEmbedding(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        hidden_size: int = 512,
        max_sequence_length: int = 30,
        dropout: float = 0.0,
        padding_idx: int = 0,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.padding_idx = padding_idx

        self.words = nn.Embedding(vocab_size, hidden_size, padding_idx=padding_idx)
        # We provide no "padding index" for position embeddigs. We zero-out
        # the positional embeddings of padded positions as a post-processing,
        self.positions = nn.Embedding(max_sequence_length, hidden_size)
        self.layer_norm = nn.LayerNorm(
            hidden_size, eps=1e-8, elementwise_affine=True
        )
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, tokens: torch.LongTensor):
        batch_size, max_sequence_length = tokens.size()
        position_indices = self.make_position_indices(
            batch_size, max_sequence_length, tokens.device
        )
        # shape: (batch_size, max_sequence_length, hidden_size)
        word_embeddings = self.words(tokens)
        position_embeddings = self.positions(position_indices)

        # shape: (batch_size, max_sequence_length, hidden_size)
        embeddings = self.layer_norm(word_embeddings + position_embeddings)
        embeddings = self.dropout(embeddings)

        # Zero-out embeddings for positions which have padding tokens.
        # shape: (batch_size, max_sequence_length, 1)
        token_mask = (tokens != self.padding_idx).unsqueeze(-1)

        # shape: (batch_size, max_sequence_length, hidden_size)
        embeddings = embeddings * token_mask.type(embeddings.dtype)
        return embeddings

    @functools.lru_cache(maxsize=128)
    def make_position_indices(
        self, batch_size: int, max_sequence_length: int, device: torch.device
    ):
        r"""
        Make position indices for a tensor containing sequence. We wrap it in
        functools' ``lru_cache`` for a slight speedup.
        """
        # Create position indices of the same size as token indices.
        positions = torch.arange(max_sequence_length, device=device)

        # shape: (batch_size, max_sequence_length)
        positions = positions.unsqueeze(0).expand(batch_size, max_sequence_length)
        return positions
