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
--main-db-id 2605e518-7e7c-8180-8f94-e478bbd126d2  \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/works.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/main_video_catalog.json \
--related-db-id 2605e518-7e7c-8172-b91e-c66c789e8e94 \
--related-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/platform_links.json \
--ids-column link_list


python 05_add_main_with_relation_async.py \
--main-db-id 2605e518-7e7c-812e-892b-f7ab2d8e3040  \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/series.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/series.json \
--related-db-id 2605e518-7e7c-8180-8f94-e478bbd126d2 \
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