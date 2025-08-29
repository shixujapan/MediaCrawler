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


python 03_generate_work_series.py \
--schema ../headers/main_video_catalog.json \
--series-schema ../headers/series.json \
--data ../data/platform_links_normalized_20250830.json \
--link-ids-file ../others/link_groups.json \
--outdir ../data



python 05_add_main_with_relation_async.py \
--main-db-id 25d5e518-7e7c-8138-8f65-c85786a3da89  \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/works.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/main_video_catalog.json \
--related-db-id 25b5e518-7e7c-811a-b79c-c0b216c39be7 \
--related-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/platform_links.json \
--ids-column link_list


python 05_add_main_with_relation_async.py \
--main-db-id 25d5e518-7e7c-81f8-b077-f84db42604c3  \
--main-csv /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/data/20250829/series.csv \
--main-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/series.json \
--related-db-id 25d5e518-7e7c-8138-8f65-c85786a3da89 \
--related-schema /Users/xu.shi/Downloads/圻夏夏/MediaCrawler/media_library/final/headers/main_video_catalog.json \
--ids-column work_id_list