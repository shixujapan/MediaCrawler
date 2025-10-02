python main.py --platform ks --lt qrcode --type creator --save_data_option json
python main.py --platform bili --lt qrcode --type creator --save_data_option json
python main.py --platform xhs --lt qrcode --type creator --save_data_option json
python main.py --platform dy --lt qrcode --type creator --save_data_option json


python main.py --platform bilibili
python main.py --platform xhs
python main.py --platform kuaishou
<!-- python main.py --platform douyin --> blocked


cd /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/scripts

python 01_pandas_batch_convert.py --input /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/data/library_20250830.csv --outdir ../data

python 02_process_titles.py --input ../data/platform_links_20250830.csv --rules ../others/rules.json --outdir ../data

python create_database.py --schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/platform_links.json --db-title "跨平台作品表" --parent-page-id 2575e5187e7c803babf7e58c5bc61613

python create_database.py --schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/main_video_catalog.json --db-title "作品一览表" --parent-page-id 2575e5187e7c803babf7e58c5bc61613

python create_database.py --schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/series.json --db-title "合集一览表" --parent-page-id 2575e5187e7c803babf7e58c5bc61613


python 05_add_main_with_relation_async.py \
--main-db-id 25b5e518-7e7c-811a-b79c-c0b216c39be7 \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/platform_links_normalized_20250829.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/platform_links.json


python 05_add_main_with_relation_async.py \
--main-db-id 25b5e518-7e7c-811a-b79c-c0b216c39be7 \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250830/platform_links_normalized_20250831.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/platform_links.json


python 03_generate_work_series.py \
--schema ../headers/main_video_catalog.json \
--series-schema ../headers/series.json \
--inputdir ../data \
--inputfiles 20250829/platform_links_normalized_20250829.json,20250830/platform_links_normalized_20250831.json \
--link-ids-file ../others/link_groups.json \
--outdir ../data


python 05_add_main_with_relation_async.py \
--main-db-id 2675e518-7e7c-8170-9a9e-c9ce100387bc  \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/works.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/main_video_catalog.json \
--related-db-id 2675e518-7e7c-8140-b31c-f47c1cfc9d34 \
--related-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/platform_links.json \
--ids-column link_list


python 05_add_main_with_relation_async.py \
--main-db-id 2675e518-7e7c-81e3-b214-c270808267e1  \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/series.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/series.json \
--related-db-id 2675e518-7e7c-8170-9a9e-c9ce100387bc \
--related-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/main_video_catalog.json \
--ids-column work_id_list


python3 /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/scripts/06_search_platform_links.py \
  --query "东栏雪,#东栏雪#快手星芒短剧" \
  --input "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/platform_links_normalized_20250829.csv,/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250830/platform_links_normalized_20250831.csv" \
  --output "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/东栏雪/search_results.json"

python3 /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/scripts/06_search_platform_links.py \
  --query "长公主在上" \
  --input "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/platform_links_normalized_20250829.csv,/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250830/platform_links_normalized_20250831.csv" \
  --output "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/长公主在上/search_results.json"

python3 /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/scripts/06_search_platform_links.py \
  --query "月白之时" \
  --input "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/platform_links_normalized_20250829.csv,/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250830/platform_links_normalized_20250831.csv" \
  --output "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/月白之时/search_results.json"

python3 /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/scripts/06_search_platform_links.py \
  --query "浮华梦" \
  --input "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/platform_links_normalized_20250829.csv,/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250830/platform_links_normalized_20250831.csv" \
  --output "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/浮华梦/search_results.json"

python3 /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/scripts/06_search_platform_links.py \
  --query "盛世天下" \
  --input "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/platform_links_normalized_20250829.csv,/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250830/platform_links_normalized_20250831.csv" \
  --output "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/盛世天下/search_results.json"

python3 /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/scripts/06_search_platform_links.py \
  --query "出马" \
  --input "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/platform_links_normalized_20250829.csv,/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250830/platform_links_normalized_20250831.csv" \
  --output "/Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/出马/search_results.json"

  月白之时15集的LINK有问题打不开: https://www.kuaishou.com/short-video/3xbp7dyi2wfpfiu
  黄雀在后合集: id2缺快手
  抖音 合集·我的be小说男友 -> 合集·我的小说男友
  恶人组第一集，第二集，第六集缺小红书
  恶人组第二集在BiliBili没找到
  恶人组第四集在BiliBili没找到
  恶人组第七集缺抖音

  {
    "series_name": "梦幻西游手游宣传片",
    "desc":"书生x小狐狸/",
    "groups":[
      {"id":1, "duplicated_id_list": [""]},
      {"id":2, "duplicated_id_list": [""]},
      {"id":3, "duplicated_id_list": [""]},
      {"id":4, "duplicated_id_list": [""]},
      {"id":5, "duplicated_id_list": [""]}
    ]
  },

  牛年新春（小红书题目:情人节快乐）缺少
  牛年新春花絮（知竹zZ）缺少
  https://www.bilibili.com/video/BV1tX4y1572g?spm_id_from=333.788.videopod.episodes&vd_source=4263153bf5d47a089cc902f4d360c509&p=2

  {
    "series_name": "圻夏夏x圣微",
    "desc": "女侠过招",
    "groups":[
      {"id":1, "duplicated_id_list": ["87af07ae"], "remarks": ["B站"]}
    ],
    "remarks": ""
  },
