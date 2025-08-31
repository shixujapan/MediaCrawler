### 处理目标：
- 仅处理 CSV 文件中的以下三列：
    - title 列（标题）
    - tags 列（格式为 #A#B 的标签）
    - co_operators 列（格式为 A,B 的合作者）
- 输入与输出：
    - 输入文件：位于 ./data 目录下的 xxx_input.csv。
    - 输出文件：生成标准化后的文件（如 xxx_normalized_20250830.csv）。

### 数据处理流程
1. 标题列（title）处理：
    - 清理换行符和多余空格。
    - 替换中文标点为英文标点：
        - ： → :
        - ， → ,（注意：此逗号不是列的分隔符）
    - 替换中文括号为英文括号：（） → ()。
    - 移除类似 (O3x4y7uzvqsk4syy) 的 ID 标识。
2. 角色标注提取：
    - 识别 title 列中的角色标注（格式为 角色:合作者，如 🎬:残月筝 或 出镜:团子,小瑜）。
        - 🎬:残月筝
        - 出镜:团子,小瑜
            - 合作者可能会由,分隔
        - 拍摄:杨老麦
        - 🎬:@知竹zZ
            - @可能会有多个
        - 拍摄:@杨老麦
            - @可能会有多个
        - 导/摄/后:残月筝
        - 出境:夏梵/圻夏夏
            - 夏梵和圻夏夏是两个人名
        - 衣服:池夏-兰若,池夏-竹月
            - 合作者名字中会有-或_
    - 提取合作者到 co_operators 列，并去重。
    - 使用 rules.json 中的配置：
        - stop_words：过滤无效合作者（如 圻夏夏 和 我）。
        - titles：定义合法的角色名集合（如 出境、摄影、🎬 等）。
    - 最后从title里去掉角色:合作者
3. 合作者标准化：
    - 根据 rules.json 中的 normalize_coop 规则替换合作者名称（如 庄翰 → 庄翰_Roya）。
    - 处理合作者名称中的分隔符（如 、、/、,）。
4. 标签列（tags）处理：
    - 提取 title 中的标签（如 #打戏）并合并到 tags 列。
    - 如果标签去掉 # 后匹配 co_operators 或 normalize_coop 中的名称，则将其归入 co_operators 列。
    - 最中从title中去掉标签
5. 其他清理：
    - 补全未匹配的括号（如 ()、[]、【】、{}）。
    - 去重重复的标点（如 ,,）。
    - 保留原始数据中的其他列不变。
    - 如果 title 中包含 bgm： 标注，不要将其迁移到bgm列。
### 测试与生成
- 测试：
    - 使用 ./data 下的输入文件（如 platform_links_input.csv）和预期输出文件（如 platform_links_normalized_20250830.csv）进行验证。
- 使用方法：
    - 命令行接口：
        ```
        python scripts/02_process_titles.py \
        --input data/platform_links_YYYYMMDD.csv \
        --rules others/rules.json \
        --outdir ../data
        ```
    - 输出：在 --outdir 下自动生成按日期命名的文件：
        - platform_links_normalized_YYYYMMDD.csv
        - platform_links_normalized_YYYYMMDD.json
    - 创建script,用python(pandas)
- 注意事项
    - 独立性：不要参考 02_process_titles.py 和 02_process_titles_v2.py，需独立实现逻辑。
    - 覆盖范围：仅修改 title、tags、co_operators 三列，其他列保持不变。

- 示例规则
    - rules.json示例:
```
    {
        "stop_words": ["圻夏夏", "我"],
        "normalize_coop": [
            {"pattern": "夏弃疾", "replacement": "夏弃疾（下乡版）"}
        ],
        "titles": ["出境", "🎬", "👗", "导演", "策划"]
    }
```