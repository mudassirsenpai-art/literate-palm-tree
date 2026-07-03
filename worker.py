import asyncio, json, os, subprocess, time, re
import nest_asyncio
from pyrogram import Client

nest_asyncio.apply()

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0: return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"

def make_prog(app, chat_id, msg_id, label, fname, mode, task_id, user_name, user_id, res_val):
    start_t = time.time()
    last_t = start_t
    hidden_id = f"[\u200b](http://t.id/{task_id})"
    async def cb(current, total):
        nonlocal last_t
        now = time.time()
        if total and (now - last_t < 2.5) and current < total: return
        last_t = now
        
        elapsed = now - start_t
        speed_bps = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / speed_bps if speed_bps > 0 else 0
        
        pct = (current / total * 100) if total else 0
        filled = int(pct / 10)
        bar = f"[{'█' * filled}{'░' * (10 - filled)}]"
        
        text = (
            f"File name:- **{fname}**\n"
            f"{mode} {label.capitalize()}...\n"
            f"{bar}\n"
            f"Percentage: {pct:.1f}%\n"
            f"Time Elapsed: {format_time(elapsed)}\n"
            f"Eta: {format_time(eta)}\n"
            f"Speed: {format_size(speed_bps)}/s\n"
            f"Size: {format_size(current)}/{format_size(total) if total else 'Unknown'}\n"
            f"Task by: [{user_name}](tg://user?id={user_id})\n"
            f"Cancel: /cancel (Reply to this message)\n"
            f"Specs: {mode.upper()} | {res_val}{hidden_id}"
        )
        try: await app.edit_message_text(chat_id, msg_id, text)
        except Exception as e:
            err = str(e).lower()
            if "deleted" in err or "invalid" in err or "not found" in err:
                os._exit(1)
    return cb

async def prep_subtitle(s_path: str, font_setting: str) -> str:
    if not s_path or not os.path.exists(s_path): return s_path
    
    real_font_name = font_setting
    base, ext = os.path.splitext(s_path)
    ass_path = base + ".ass"
    
    if ext.lower() in ['.srt', '.vtt']:
        subprocess.run(['ffmpeg', '-y', '-i', s_path, ass_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(ass_path): return s_path
    elif ext.lower() == '.ass':
        ass_path = s_path
    else: return s_path
        
    try:
        with open(ass_path, 'r', encoding='utf-8-sig', errors='ignore') as f: lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith("Style:"):
                parts = line.split(",")
                if len(parts) > 2:
                    parts[1] = real_font_name 
                    line = ",".join(parts)
            new_lines.append(line)
        mod_path = base + "_mod.ass"
        with open(mod_path, 'w', encoding='utf-8') as f: f.writelines(new_lines)
        return mod_path
    except Exception: return ass_path

def get_wm_coords(pos, is_text=False, custom_val="10:10"):
    if pos == 'custom':
        parts = str(custom_val).split(':')
        if len(parts) == 2: return parts[0], parts[1]

    tw = "tw" if is_text else "w"
    th = "th" if is_text else "h"
    W = "w" if is_text else "W"
    H = "h" if is_text else "H"
    pad = "10"
    
    if pos == 'top-left': return pad, pad
    if pos == 'top-center': return f"({W}-{tw})/2", pad
    if pos == 'top-right': return f"{W}-{tw}-{pad}", pad
    if pos == 'center-left': return pad, f"({H}-{th})/2"
    if pos == 'center': return f"({W}-{tw})/2", f"({H}-{th})/2"
    if pos == 'center-right': return f"{W}-{tw}-{pad}", f"({H}-{th})/2"
    if pos == 'bottom-left': return pad, f"{H}-{th}-{pad}"
    if pos == 'bottom-center': return f"({W}-{tw})/2", f"{H}-{th}-{pad}"
    if pos == 'bottom-right': return f"{W}-{tw}-{pad}", f"{H}-{th}-{pad}"
    return pad, pad

async def main():
    api_id_str = os.environ.get("API_ID", "0")
    api_id = int(api_id_str) if api_id_str.isdigit() else 0
    api_hash = os.environ.get("API_HASH", "")
    bot_token = os.environ.get("BOT_TOKEN", "")
    
    app = Client("gh_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
    await app.start()
    
    chat_id = int(os.environ.get("CHAT_ID", "0"))
    v_id = int(os.environ.get("VIDEO_MSG_ID", "0"))
    s_id = os.environ.get("SUB_MSG_ID", "")
    a_id = os.environ.get("AUDIO_MSG_ID", "")
    
    msg_id_str = os.environ.get("STATUS_MSG_ID", "0")
    msg_id = int(msg_id_str) if msg_id_str and msg_id_str.isdigit() else 0
    
    task_id = os.environ.get("TASK_ID", "")
    mode = os.environ.get("MODE", "")
    font_file_id = os.environ.get("FONT_FILE_ID", "")
    wm_file_id = os.environ.get("WM_FILE_ID", "")
    thumb_file_id = os.environ.get("THUMB_FILE_ID", "")
    
    settings = json.loads(os.environ.get('INPUT_SETTINGS', '{}'))
    out_name = settings.get("output", "output.mkv")
    user_name = settings.get("user_name", "Admin")
    user_id = settings.get("user_id", "0")
    res_val = settings.get("res", "Auto")
    hidden_id = f"[\u200b](http://t.id/{task_id})"
    
    if font_file_id:
        f_path = await app.download_media(font_file_id, file_name="fonts/custom_font.ttf")
        if f_path:
            os.makedirs(os.path.expanduser("~/.fonts"), exist_ok=True)
            os.system(f"cp '{f_path}' ~/.fonts/ && fc-cache -f -v 2>/dev/null")
            try:
                proc = subprocess.run(['fc-scan', '-f', '%{family}', f_path], capture_output=True, text=True)
                out_str = proc.stdout.strip()
                if out_str: settings['font'] = out_str.split(',')[0].strip()
            except: pass

    wm_path = None
    if wm_file_id and settings.get('wm_type') == 'image':
        wm_path = await app.download_media(wm_file_id, file_name="wm.png")
    
    v_msg = await app.get_messages(chat_id, v_id)
    v_path = await app.download_media(v_msg, file_name="input.mp4", progress=make_prog(app, chat_id, msg_id, "Downloading", out_name, mode, task_id, user_name, user_id, res_val) if msg_id else None)
    
    thumb_path = None
    if thumb_file_id and settings.get('thumb_mode') == 'custom':
        thumb_path = await app.download_media(thumb_file_id, file_name="thumb.jpg")
    elif settings.get('thumb_mode', 'original') == 'original' and v_path:
        try:
            _dur_probe = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_entries', 'format=duration', v_path],
                capture_output=True, text=True
            )
            _dur_secs = float(json.loads(_dur_probe.stdout).get('format', {}).get('duration', 0))
            _thumb_ts = max(_dur_secs * 0.03, 1.0)
            _h = int(_thumb_ts // 3600); _m = int((_thumb_ts % 3600) // 60); _s = _thumb_ts % 60
            _ts_str = f"{_h:02d}:{_m:02d}:{_s:06.3f}"
            subprocess.run(['ffmpeg', '-y', '-i', v_path, '-ss', _ts_str, '-vframes', '1', 'thumb.jpg'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists('thumb.jpg'):
                thumb_path = 'thumb.jpg'
        except: pass
        
    s_path = None
    if s_id:
        s_msg = await app.get_messages(chat_id, int(s_id))
        ext = ".srt"
        if getattr(s_msg.document, "file_name", ""):
            if s_msg.document.file_name.endswith(".ass"): ext = ".ass"
            elif s_msg.document.file_name.endswith(".vtt"): ext = ".vtt"
        orig_s_path = await app.download_media(s_msg, file_name=f"sub{ext}", progress=make_prog(app, chat_id, msg_id, "Downloading", out_name, mode, task_id, user_name, user_id, res_val) if msg_id else None)
        s_path = await prep_subtitle(orig_s_path, settings.get("font", "Arial"))
        
    a_path = None
    if a_id and mode == 'addaudio':
        a_msg = await app.get_messages(chat_id, int(a_id))
        a_path = await app.download_media(a_msg, file_name=f"audio.m4a", progress=make_prog(app, chat_id, msg_id, "Downloading", out_name, mode, task_id, user_name, user_id, res_val) if msg_id else None)
    
    cmd = ['ffmpeg', '-y', '-i', v_path]
    
    is_shell = False
    custom_args = settings.get('custom_args', '')

    if mode in ['extractsubs', 'extractaudio']:
        if msg_id: await app.edit_message_text(chat_id, msg_id, f"🔍 Probing tracks...\nSpecs: {mode.upper()} | {res_val}{hidden_id}")
        stream_type = 's' if mode == 'extractsubs' else 'a'
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', stream_type,
             '-show_entries', 'stream=index,codec_name,tags',
             '-of', 'json', v_path],
            capture_output=True, text=True
        )
        try: streams = json.loads(probe.stdout).get('streams', [])
        except: streams = []

        if not streams:
            if msg_id:
                try: await app.edit_message_text(chat_id, msg_id, f"❌ No tracks found in **{out_name}**{hidden_id}")
                except: pass
            await app.stop()
            return

        base_name = os.path.splitext(out_name)[0]
        ext_map = {'subrip': 'srt', 'ass': 'ass', 'webvtt': 'vtt',
                   'aac': 'm4a', 'opus': 'ogg', 'mp3': 'mp3',
                   'ac3': 'ac3', 'eac3': 'eac3', 'flac': 'flac', 'dts': 'dts'}
        extracted_files = []

        for s in streams:
            idx = s.get('index')
            codec = s.get('codec_name', 'srt' if mode == 'extractsubs' else 'aac')
            tags = s.get('tags') or {}
            lang = tags.get('language', f'trk{idx}')
            file_ext = ext_map.get(codec, 'mkv' if mode == 'extractsubs' else 'mka')

            if mode == 'extractsubs':
                track_out = f"{base_name}_track#{idx}_{lang}.{file_ext}"
            else:
                track_out = f"{base_name}_audiotrack#{idx}_{lang}.{file_ext}"

            if msg_id:
                try: await app.edit_message_text(chat_id, msg_id, f"⚙️ Extracting track {idx} ({lang})...\nSpecs: {mode.upper()}{hidden_id}")
                except: pass

            p = subprocess.run(
                ['ffmpeg', '-y', '-i', v_path, '-map', f'0:{idx}', '-c', 'copy', track_out],
                capture_output=True
            )
            if os.path.exists(track_out):
                extracted_files.append((track_out, idx, lang))

        for (fpath, idx, lang) in extracted_files:
            lbl = "Subtitle" if mode == 'extractsubs' else "Audio"
            for attempt in range(3):
                try:
                    await app.send_document(chat_id, fpath, caption=f"✅ Extracted {lbl}\n🎬 `{out_name}`\n🏷️ Track: {idx} | Lang: {lang}", file_name=os.path.basename(fpath))
                    break
                except Exception:
                    await asyncio.sleep(5)

        if msg_id:
            try: await app.delete_messages(chat_id, msg_id)
            except: pass
        await app.stop()
        return

    if mode == 'rename':
        cmd += ['-c', 'copy']
    elif mode == 'removeaudio':
        track = settings.get('audio_track', 'all')
        if track == 'all': cmd += ['-c', 'copy', '-an']
        else: cmd += ['-map', '0', '-map', f'-0:a:{track}', '-c', 'copy']
    elif mode == 'addaudio' and a_path:
        cmd += ['-i', a_path, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac']
    else:
        vf_chains = []
        if res_val == "Original": res_val = settings.get("cpu_res", "original")
        if res_val.lower() != "original":
            rmap = {"1080p":"1920:1080", "720p":"1280:720", "480p":"854:480", "360p":"640:360", "240p":"426:240", "144p":"256:144"}
            vf_chains.append(f"scale={rmap.get(res_val.lower(), res_val)}")
        
        if s_path:
            esc_sub = s_path.replace("\\\\", "/").replace("'", r"'\''").replace(":", r"\\:")
            fonts_dir = os.path.abspath("fonts").replace("\\\\", "/").replace(":", r"\\:") if font_file_id else ""
            font_arg = f":fontsdir='{fonts_dir}'" if fonts_dir else ""
            vf_chains.append(f"subtitles='{esc_sub}'{font_arg}")

        wm_type = settings.get('wm_type', 'none')
        wm_pos = settings.get('wm_pos', 'top-right')
        wm_size = settings.get('wm_size', '25')
        
        custom_pos = settings.get('wm_custom_pos', '10:10')
        if wm_type == 'text' and settings.get('wm_text'):
            x, y = get_wm_coords(wm_pos, is_text=True, custom_val=custom_pos)
            vf_chains.append(f"drawtext=text='{settings['wm_text']}':fontsize={wm_size}:fontcolor=white:x={x}:y={y}")

        if wm_type == 'image' and wm_path:
            cmd.extend(['-i', wm_path])
            x, y = get_wm_coords(wm_pos, is_text=False, custom_val=custom_pos)
            
            if settings.get('wm_rembg'):
                ck_c = settings.get('wm_bg_color', '0x000000')
                ck_s = settings.get('wm_bg_sim', '0.1')
                ck_b = settings.get('wm_bg_blend', '0.1')
                fc = f"[1:v]colorkey={ck_c}:{ck_s}:{ck_b},scale=-1:{wm_size}[wm];[0:v]"
            else:
                fc = f"[1:v]scale=-1:{wm_size}[wm];[0:v]"
                
            if vf_chains: fc += ",".join(vf_chains) + "[vbase];[vbase][wm]overlay="
            else: fc += "[wm]overlay="
            fc += f"{x}:{y}"
            cmd += ['-filter_complex', fc]
        else:
            if vf_chains: cmd += ['-vf', ",".join(vf_chains)]
        
        if mode == 'customcmd' and custom_args:
            if '&&' in custom_args or custom_args.startswith('ffmpeg'):
                is_shell = True
                shell_cmd = custom_args.replace("INPUT", v_path).replace("OUTPUT", out_name)
                import shlex
                try:
                    last_w = shlex.split(shell_cmd)[-1]
                    if '.' in last_w and not last_w.startswith('-'): out_name = last_w
                except: pass
            else:
                import shlex
                c_args = shlex.split(custom_args)
                if len(c_args) > 0 and not c_args[-1].startswith('-') and '.' in c_args[-1]:
                    out_name = c_args.pop()
                cmd += c_args
        else:
            crf = str(settings.get("quality", "23"))
            preset = settings.get("preset", "fast")
            ac = settings.get("audio_codec", "copy")
            cmd += ['-c:v', 'libx264', '-preset', preset, '-crf', crf]
            if ac == 'copy': cmd += ['-c:a', 'copy']
            else: cmd += ['-c:a', ac, '-b:a', settings.get('audio_bitrate', '128k')]

    if not is_shell and mode != 'customcmd':
        if settings.get('remove_softsubs', False): cmd += ['-sn']
        if settings.get('meta_clean', False): cmd += ['-map_metadata', '-1']
        if settings.get('meta_title') and str(settings['meta_title']) != 'None': cmd += ['-metadata', f'title={settings["meta_title"]}']
        if settings.get('meta_author') and str(settings['meta_author']) != 'None': cmd += ['-metadata', f'artist={settings["meta_author"]}']
        
    if not is_shell: cmd += [out_name]
    
    if msg_id: await app.edit_message_text(chat_id, msg_id, f"File name:- **{out_name}**\nEncoding :- [░░░░░░░░░░] 0.0%\nSpecs: {mode.upper()} | {res_val}{hidden_id}")
    
    dur_proc = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_entries', 'format=duration', v_path], capture_output=True, text=True)
    try: dur = float(json.loads(dur_proc.stdout).get('format', {}).get('duration', 0))
    except: dur = 0.0

    if is_shell:
        print(f"RUNNING SHELL COMMAND: {shell_cmd}")
        proc = await asyncio.create_subprocess_shell(shell_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    else:
        print(f"RUNNING FFMPEG COMMAND: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        
    last_edit = 0.0
    dur_proc_time = time.time()
    
    error_log = ""
    
    while True:
        try:
            line = await proc.stdout.readuntil(b'\r')
        except asyncio.exceptions.IncompleteReadError as e:
            line = e.partial
        if not line: break
        
        dec = line.decode(errors='replace')
        error_log += dec
        if len(error_log) > 1000: error_log = error_log[-1000:]
        
        match = re.search(r"time=\s*(\d+:\d+:\d+\.\d+)", dec)
        match_speed = re.search(r"speed=\s*(\d+\.?\d*x)", dec)
        speed_str = match_speed.group(1) if match_speed else "1.0x"
        
        if match and dur > 0 and msg_id:
            time_str = match.group(1)
            h, m, s = map(float, time_str.split(':'))
            curr_sec = h*3600 + m*60 + s
            now = time.time()
            if now - last_edit >= 3.0:
                last_edit = now
                
                elapsed = now - dur_proc_time
                avg_speed = curr_sec / elapsed if elapsed > 0 else 1
                eta = (dur - curr_sec) / avg_speed if avg_speed > 0 else 0
                
                pct = min((curr_sec / dur) * 100, 100)
                filled = int(pct / 10)
                bar = f"[{'█' * filled}{'░' * (10 - filled)}]"
                
                text = (
                    f"File name:- **{out_name}**\n"
                    f"{mode} Encoding...\n"
                    f"{bar}\n"
                    f"Percentage: {pct:.1f}%\n"
                    f"Time Elapsed: {format_time(elapsed)}\n"
                    f"Eta: {format_time(eta)}\n"
                    f"Speed: {speed_str}\n"
                    f"Frame: {format_time(curr_sec)}/{format_time(dur)}\n"
                    f"Task by: [{user_name}](tg://user?id={user_id})\n"
                    f"Specs: {mode.upper()} | {res_val}{hidden_id}"
                )
                try: await app.edit_message_text(chat_id, msg_id, text)
                except Exception as e:
                    err = str(e).lower()
                    if "deleted" in err or "invalid" in err or "not found" in err:
                        os._exit(1)

    await proc.wait()
    
    if proc.returncode != 0:
        if msg_id:
            try: await app.edit_message_text(chat_id, msg_id, f"❌ **FFmpeg Error**\n`{error_log[-300:]}`{hidden_id}")
            except: pass
        await app.stop()
        return
    
    if msg_id:
        try: await app.edit_message_text(chat_id, msg_id, f"File name:- **{out_name}**\nUploading... [░░░░░░░░░░] 0.0%\nSpecs: {mode.upper()} | {res_val}{hidden_id}")
        except: pass

    for attempt in range(3):
        try:
            await app.send_document(
                chat_id, out_name,
                caption=f"✅ **{out_name}**",
                file_name=out_name,
                thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                progress=make_prog(app, chat_id, msg_id, "Uploading", out_name, mode, task_id, user_name, user_id, res_val) if msg_id else None
            )
            break
        except Exception as e:
            if attempt == 2:
                if msg_id:
                    try: await app.edit_message_text(chat_id, msg_id, f"❌ Upload failed after 3 tries: {e}{hidden_id}")
                    except: pass
            else:
                await asyncio.sleep(10)
    
    if msg_id:
        try: await app.delete_messages(chat_id, msg_id)
        except: pass
    
    await app.stop()

asyncio.run(main())
