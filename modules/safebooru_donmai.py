from modules.danbooru_with_tags import init
from modules.danbooru_with_tags import runBooru

arguments_dictionary = {
    "log_file_name": "booru-dl.log",
    "normal_posts_url": "https://safebooru.donmai.us/posts?",
    "login_element_id": "session_name",
    "login_element_name": "session[name]",
    "password_element_name": "session[password]",
    "pagination_info": ("div", "class", "paginator"),
    "base_url": "https://safebooru.donmai.us",
    "preview_info": ("article", "class", "post-preview"),
    "artist_tag": ("li", "class", "tag-type-1"),
    "character_tag": ("li", "class", "tag-type-4"),
    "series_tag": ("li", "class", "tag-type-3"),
    "tag_element": ("li", "class", "tag-type-0"),
    "source_id": "post-information",
    "source_index": 3,
    "tag_element_name": "data-tag-name",
    "full_image_id": "post-option-download",
    "login_url": "https://safebooru.donmai.us/login",
    "post_url": "https://safebooru.donmai.us/session",
}

init(**arguments_dictionary)
