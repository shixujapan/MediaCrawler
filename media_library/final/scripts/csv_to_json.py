import pandas as pd

base_path = "../data/"
# Read CSV file
df = pd.read_csv(base_path + "platform_links_normalized.csv")

# Convert to JSON string (pretty-printed, keep Chinese characters)
json_str = df.to_json(orient="records", force_ascii=False, indent=2)

# Save JSON to file
with open(base_path + "platform_links_normalized.json", "w", encoding="utf-8") as f:
    f.write(json_str)


# import uuid
# import pandas as pd

# def convert_uuid_column(input_csv, output_csv, column_name="uuid"):
#     # 读取原始CSV
#     df = pd.read_csv(input_csv)

#     # 转换指定列
#     df[column_name] = df[column_name].apply(lambda x: str(uuid.UUID(hex=str(x).strip())))

#     # 保存结果
#     df.to_csv(output_csv, index=False)
#     print(f"已转换完成，结果保存在: {output_csv}")

# if __name__ == "__main__":
#     # 示例用法：把 input.csv 中的 uuid 列转换后输出到 output.csv
#     convert_uuid_column("input.csv", "output.csv", column_name="uuid")