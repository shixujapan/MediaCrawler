# -*- coding: utf-8 -*-
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# 小红书平台配置

# 排序方式，具体的枚举值在media_platform/xhs/field.py中
SORT_TYPE = "popularity_descending"

# 指定笔记URL列表, 必须要携带xsec_token参数
XHS_SPECIFIED_NOTE_URL_LIST = [
    # "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=&xsec_source=pc_search"
    # 合集（答案之书）
    "https://www.xiaohongshu.com/explore/62d38f43000000002103f7a8?xsec_token=ABBWLkze5wXprAwsL5u9SjLhclBZUVWwOPb_DGawRCEQE=&xsec_source=pc_search",
    # 一般
    "https://www.xiaohongshu.com/explore/6124bc8c0000000021037961?xsec_token=ABF9R9ww3KmcpFPNYcCwOnczdX-4NpVNN4OIl1__iWzhI=&xsec_source=pc_search",
    # 图
    "https://www.xiaohongshu.com/explore/62875ec1000000002103fc59?xsec_token=ABPDnxLtuIXFzfvQODnzkHbMURyiWGaZV0QByQQNPaOwk=&xsec_source=pc_search"
    # ........................
]

# 指定用户ID列表
XHS_CREATOR_ID_LIST = [
    # 圻夏夏
    # "5c64214e0000000012002203",
    # 知竹zZ
    "57cce96182ec3957bce8bf35",
    # 盛世天下
    "6535c98400000000060075e1"
    # ........................
]
