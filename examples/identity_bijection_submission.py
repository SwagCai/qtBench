# Signature template for the exchanging_bijection task. The identity map is a
# valid bijection but does NOT exchange area and bounce, so it fails scoring at
# the numerical stage; it only shows the required forward/inverse shape.
def forward(path):
    return path


def inverse(path):
    return path
