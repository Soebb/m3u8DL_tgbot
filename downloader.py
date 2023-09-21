import os
import logging
import subprocess
import pathlib
import ffmpeg
import uuid
import time
import random
import fakeredis
from pathlib import Path
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from io import StringIO
from tqdm import tqdm


def ytdl_download(url: str, tempdir: str):
    if url.endswith('.m3u8'):
        try:
            # Build download command as argument list
            download_command = ["./N_m3u8DL-RE", url, "--save-dir", tempdir]
            print("N_m3u8DL is being used to download videos in m3u8 format: ", url)
            # Execute download command
            subprocess.run(download_command, check=True)
            # Get the downloaded file list
            video_paths = list(pathlib.Path(tempdir).glob("*"))

            
            # Test code: print downloaded video file list
            for video_path in video_paths:
                print(f"Download completed: {video_path}")
            return video_paths
        except Exception as e:
            raise Exception(f" N_m3u8DL Download failed for m3u8 URL: {url} - {str(e)}")

def gen_cap(bm, url, video_path):
    video_path = Path(video_path)
    chat_id = bm.chat.id
    user = bm.chat
    try:
        user_info = "@{}({})-{}".format(user.username or "N/A", user.first_name or "" + user.last_name or "", user.id)
    except Exception:
        user_info = ""

    if isinstance(video_path, pathlib.Path):
        meta = get_metadata(video_path)
        file_name = video_path.name
        file_size = sizeof_fmt(os.stat(video_path).st_size)
        print("size_instance: ", file_size)
    else:
        file_name = getattr(video_path, "file_name", "")
        file_size = sizeof_fmt(getattr(video_path, "file_size", (2 << 2) + ((2 << 2) + 1) + (2 << 5)))
        print("size_not_instance: ", file_size)
        meta = dict(
            width=getattr(video_path, "width", 0),
            height=getattr(video_path, "height", 0),
            duration=getattr(video_path, "duration", 0),
            thumb=getattr(video_path, "thumb", None),
        )
        
    file_name_without_extension = os.path.splitext(file_name)[0]
    cap = (
            f"{file_name_without_extension}\n\n{url}\t"
    )
    return cap, meta

def get_metadata(video_path):
    width, height, duration = 1280, 720, 0
    try:
        video_streams = ffmpeg.probe(video_path, select_streams="v")
        for item in video_streams.get("streams", []):
            height = item["height"]
            width = item["width"]
        duration = int(float(video_streams["format"]["duration"]))
    except Exception as e:
        logging.error(e)
    try:
        thumb = pathlib.Path(video_path).parent.joinpath(f"{uuid.uuid4().hex}-thunmnail.png").as_posix()
        ffmpeg.input(video_path, ss=duration / 2).filter("scale", width, -1).output(thumb, vframes=1).run()
    except ffmpeg._run.Error:
        thumb = None

    return dict(height=height, width=width, duration=duration, thumb=thumb)

def sizeof_fmt(num: int, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)

def upload_hook(current, total, bot_msg):
    text = tqdm_progress("Uploading...", total, current)
    edit_text(bot_msg, text) 

def tqdm_progress(desc, total, finished, speed="", eta=""):
    def more(title, initial):
        if initial:
            return f"{title} {initial}"
        else:
            return ""

    f = StringIO()
    tqdm(
        total=total,
        initial=finished,
        file=f,
        ascii=False,
        unit_scale=True,
        ncols=30,
        bar_format="{l_bar}{bar} |{n_fmt}/{total_fmt} ",
    )
    raw_output = f.getvalue()
    tqdm_output = raw_output.split("|")
    progress = f"`[{tqdm_output[1]}]`"
    detail = tqdm_output[2].replace("[A", "")
    text = f"""
{desc}

{progress}
{detail}
{more("Speed:", speed)}
{more("ETA:", eta)}
    """
    f.close()
    return text



r = fakeredis.FakeStrictRedis()

def edit_text(bot_msg, text: str):
    key = f"{bot_msg.chat.id}-{bot_msg.id}"
    # if the key exists, we shouldn't send edit message
    if not r.exists(key):
        time.sleep(random.random())
        r.set(key, "ok", ex=3)
        bot_msg.edit_text(text)

def gen_video_markup():
    markup = InlineKeyboardMarkup(
        [
            [  # First row
                InlineKeyboardButton(  # Generates a callback query when pressed
                    "convert to audio", callback_data="convert"
                )
            ]
        ]
    )
    return markup