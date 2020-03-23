from modules.danbooru_with_tags import init
from modules.danbooru_with_tags import runBooru

arguments_dictionary = {
    "log_file_name": "booru-dl.log",
    "normal_posts_url": "https://sakugabooru.com/post?",
    "login_element_id": "user_name",
    "login_element_name": "user[name]",
    "password_element_name": "user[password]",
    "pagination_info": ("div", "class", "pagination"),
    "base_url": "https://sakugabooru.com",
    "preview_info": ("div", "class", "inner"),
    "artist_tag": ("li", "class", "tag-link tag-type-artist"),
    "character_tag": ("li", "class", "tag-link tag-type-character"),
    "series_tag": ("li", "class", "tag-link tag-type-copyright"),
    "tag_element": ("li", "class", "tag-link tag-type-general"),
    "source_id": "stats",
    "source_index": 3,
    "tag_element_name": "data-name",
    "full_image_id": "highres",
    "login_url": "https://www.sakugabooru.com/user/login",
    "post_url": "https://www.sakugabooru.com/user/authenticate",
}

init(**arguments_dictionary)
