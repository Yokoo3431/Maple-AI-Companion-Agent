"""M0 冒烟测试:主包可导入。"""

import maple_agent


def test_version_present():
    assert maple_agent.__version__
