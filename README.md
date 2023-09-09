# Arcface face detection and recognition model that just works out of the box.

This is a minimalistic inference-focused repack of [link](https://github.com/deepinsight/insightface/tree/d76bc7f9ff223bcab5f19d220cd690e66098a22c).

# Supported features

- Extract face embedding for a single-face image. 
- Pretrained model with ResNet100 on MS1M [line](https://drive.google.com/file/d/1SIS-x1w0fP9ReZISR87GjjxuEWUiYyXh/view?usp=share_link) 

# Fixes and improvements over orignal version

- Everything that is not required for inference is removed
- Original version crashed with unintelligible `segmentation fault` if output of the face detector was wrong or empty. This version fixed this issuet

# How to use:

Please check example in deploy/test.py
