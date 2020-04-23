from typing import Any, List, Optional

from yacs.config import CfgNode as CN


class Config(object):
    r"""
    This class provides package-wide configuration management. It is a
    nested dict-like structure with nested keys accessible as attributes. It
    contains sensible default values, which can be modified by (first) a YAML
    file and (second) a list of attributes and values.

    An instantiated object is _immutable_: modifying any attribute is illegal.
    You must override required parameter values either through ``config_file``
    or ``override_list`` arguments. For adding more parameters at runtime
    (based on existing parameters), modify :meth:`add_derived_params`.

    Parameters
    ----------
    config_file: str
        Path to a YAML file containing configuration parameters to override.
    config_override: List[Any], optional (default = [])
        A list of sequential attributes and values of parameters to override.
        This happens after overriding from YAML file.

    Examples
    --------
    Let a YAML file named "config.yaml" specify these parameters to override::

        OPTIM:
          BATCH_SIZE: 512
          LR: 0.01

    >>> _C = Config("config.yaml", ["OPTIM.BATCH_SIZE", 1024])
    >>> _C.LR  # default: 0.001
    0.01
    >>> _C.OPTIM.BATCH_SIZE  # default: 256, file: 512
    1024
    """

    def __init__(
        self, config_file: Optional[str] = None, override_list: List[Any] = []
    ):
        _C = CN()

        # Random seed for NumPy and PyTorch, important for reproducibility.
        _C.RANDOM_SEED = 0
        # Opt level for mixed precision training using NVIDIA Apex. This can be
        # one of {0, 1, 2}. Refer NVIDIA Apex docs for their meaning.
        _C.FP16_OPT = 2

        # ---------------------------------------------------------------------
        #   Data paths and parameters related to dataloading.
        # ---------------------------------------------------------------------
        _C.DATA = CN()

        # Path to the dataset root, which structure as per README. Path is
        # assumed to be relative to project root.
        _C.DATA.ROOT = "datasets/coco"
        # Path to .vocab file generated by ``sentencepiece``.
        _C.DATA.TOKENIZER_VOCAB = "datasets/vocab/coco_10k.vocab"
        # Path to .model file generated by ``sentencepiece``.
        _C.DATA.TOKENIZER_MODEL = "datasets/vocab/coco_10k.model"

        # Size of the image (square) to crop from original input image.
        _C.DATA.IMAGE_CROP_SIZE = 224
        # Maximum length of input caption (number of tokens).
        # Longer captions will be truncated up to this length.
        _C.DATA.MAX_CAPTION_LENGTH = 30

        # COCO Captions has five captions per image. If ``True``, training will
        # use one random caption per image (data efficiency ablations).
        _C.DATA.USE_SINGLE_CAPTION = False
        # Percentage of dataset to use for training (data efficiency ablations).
        _C.DATA.USE_PERCENTAGE = 100.0

        # List of image transforms (pre-processing and data augmentation) to be
        # applied sequentially (always or randomly) during training and
        # validation. Refer ``virtex/facetories.py`` for all possible transforms.
        _C.DATA.IMAGE_TRANSFORM_TRAIN = [
            "random_resized_crop",
            "horizontal_flip",
            "color_jitter",
            "normalize",
        ]
        _C.DATA.IMAGE_TRANSFORM_VAL = [
            "smallest_resize",
            "center_crop",
            "normalize",
        ]

        # Hyper-parameters for word masking pretext. These are only used when
        # ``MODEL.NAME`` is "word_masking".
        _C.DATA.WORD_MASKING = CN()
        # Fraction of tokens to choose for masking, this must be less than 1.
        _C.DATA.WORD_MASKING.MASK_PROPORTION = 0.15
        # Probability to replace chosen tokens with [MASK] token.
        _C.DATA.WORD_MASKING.MASK_PROBABILITY = 0.85
        # Probability to replace chosen tokens with a random token.
        _C.DATA.WORD_MASKING.REPLACE_PROBABILITY = 0.10

        # ---------------------------------------------------------------------
        #   Model architecture: visual backbone and textual head.
        # ---------------------------------------------------------------------
        _C.MODEL = CN()

        # Name of model, based on pretraining task.
        # Possible choices: {"token_classification", "instance_classification",
        # "captioning", "bicaptioning", "word_masking"}
        _C.MODEL.NAME = "bicaptioning"

        _C.MODEL.VISUAL = CN()
        # Name of visual backbone. Possible choices: {"blind", "torchvision"}
        # Models from torchvision can be specified as shown below.
        _C.MODEL.VISUAL.NAME = "torchvision::resnet50"
        # Number of channels in pooled spatial features of visual backbone.
        _C.MODEL.VISUAL.FEATURE_SIZE = 2048
        # Whether to load ImageNet pretrained weights into visual backbone.
        _C.MODEL.VISUAL.PRETRAINED = False
        # Whether to keep visual backbone frozen and train only textual head.
        _C.MODEL.VISUAL.FROZEN = False

        _C.MODEL.TEXTUAL = CN()
        # Name of textual head. Set to "none" for MODEL.NAME = "*_classification".
        # Possible choices: {"transformer_postnorm", "transformer_prenorm"}.
        # Architectural hyper-parameters are specified as shown above.
        _C.MODEL.TEXTUAL.NAME = "transformer_postnorm::L1_H1024_A16_F4096"
        # L = Number of layers in the transformer.
        # H = Hidden size of the transformer (embeddings, attention features).
        # A = Number of attention heads in the transformer.
        # F = Size of feedforward layers in the transformer.
        # Typically, we have (A = H / 64) and (F = 4 * H).

        # Dropout probability for embedding, hidden features in textual head.
        _C.MODEL.TEXTUAL.DROPOUT = 0.1

        # ---------------------------------------------------------------------
        #   Optimization hyper-parameters, default values are for pretraining
        #   our best model on bicaptioning task (COCO Captions).
        # ---------------------------------------------------------------------
        _C.OPTIM = CN()

        # Name of optimizer to use. Supported values: {"sgd", "adamw"}.
        # AdamW uses default (beta1, beta2) values from PyTorch.
        _C.OPTIM.OPTIMIZER_NAME = "sgd"
        # Momentum co-efficient for SGD. Ignored for AdamW.
        _C.OPTIM.SGD_MOMENTUM = 0.9
        # Weight decay co-efficient for the optimizer.
        _C.OPTIM.WEIGHT_DECAY = 0.0001
        # Regex pattern of params for which there will be no weight decay.
        _C.OPTIM.NO_DECAY = ".*textual.*(norm.*|bias)"
        # Max gradient norm for clipping to avoid exploding gradients.
        _C.OPTIM.CLIP_GRAD_NORM = 10

        # Wrap our optimizer with LookAhead (https://arxiv.org/abs/1907.08610).
        _C.OPTIM.USE_LOOKAHEAD = False
        _C.OPTIM.LOOKAHEAD_ALPHA = 0.5
        _C.OPTIM.LOOKAHEAD_STEPS = 5

        # We set different learning rates for CNN (visual backbone) and rest of
        # the model. CNN LR is typically much higher for training from scratch.
        # Both LRs undergo same warmup-decay schedules.

        # Total batch size (will be distributed evenly across GPUs).
        _C.OPTIM.BATCH_SIZE = 256
        # Max learning rate for CNN (visual backbone).
        _C.OPTIM.CNN_LR = 0.2
        # Max learning rate for rest of the model.
        _C.OPTIM.LR = 0.001
        # Number of iterations to train for, batches are randomly sampled.
        _C.OPTIM.NUM_ITERATIONS = 500000

        # Number of steps at the start of training for linear LR warmup.
        _C.OPTIM.WARMUP_STEPS = 10000
        # Learning rate annealing schedule for decay after warmup.
        # Possible choices: {"none", "linear", "cosine", "multistep"}.
        _C.OPTIM.LR_DECAY_NAME = "cosine"
        # Steps to decay LR for "multistep" schedule.
        _C.OPTIM.LR_STEPS = []
        # Factor to multiply with LR for "multistep" schedule.
        _C.OPTIM.LR_GAMMA = 0.1

        # Override parameter values from YAML file first, then from override
        # list, then add derived params.
        self._C = _C
        if config_file is not None:
            self._C.merge_from_file(config_file)
        self._C.merge_from_list(override_list)

        self.add_derived_params()

        # Make an instantiated object of this class immutable.
        self._C.freeze()

    def add_derived_params(self):
        r"""Add parameters with values derived from existing parameters."""

        # We don't have any such cases so far.
        pass

    def dump(self, file_path: str):
        r"""Save config at the specified file path.

        Parameters
        ----------
        file_path: str
            (YAML) path to save config at.
        """
        self._C.dump(stream=open(file_path, "w"))

    def __getattr__(self, attr: str):
        return self._C.__getattr__(attr)

    def __str__(self):
        return self._C.__str__()

    def __repr__(self):
        return self._C.__repr__()
