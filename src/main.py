import os
import mimetypes
from datetime import datetime
from flask import Flask, render_template, send_from_directory, abort, url_for, redirect


def sizeof_fmt(num):
	try:
		num = float(num)
	except Exception:
		return "—"
	for unit in ["B", "KB", "MB", "GB", "TB"]:
		if num < 1024.0:
			if unit == "B":
				return f"{int(num)} {unit}"
			return f"{num:.1f} {unit}"
		num /= 1024.0
	return f"{num:.1f} PB"


def map_type(is_dir, name):
	if is_dir:
		return "Folder"
	ext = os.path.splitext(name)[1].lower()
	mapping = {
		".txt": "Text File",
		".md": "Text File",
		".rst": "Text File",
		".pdf": "PDF",
		".doc": "Document",
		".docx": "Document",
		".xls": "Spreadsheet",
		".xlsx": "Spreadsheet",
		".ppt": "Presentation",
		".pptx": "Presentation",
		".csv": "Data",
		".json": "Data",
		".xml": "Data",
		".zip": "Compressed",
		".tar": "Compressed",
		".gz": "Compressed",
		".7z": "Compressed",
		".rar": "Compressed",
		".jpg": "Image",
		".jpeg": "Image",
		".png": "Image",
		".gif": "Image",
		".svg": "Image",
		".webp": "Image",
		".mp4": "Video",
		".mkv": "Video",
		".mov": "Video",
		".mp3": "Audio",
		".wav": "Audio",
		".flac": "Audio",
		".exe": "Executable",
		".sh": "Script",
		".py": "Code",
		".js": "Code",
		".ts": "Code",
		".html": "Web",
		".css": "Web",
	}
	return mapping.get(ext, "File")


def dir_contains_hide(path):

	if not os.path.isdir(path):
		return False
	for root, dirs, files in os.walk(path):
		if ".hide" in files:
			return True
	return False


HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_BASE = os.path.abspath(os.path.join(HERE, ".."))


def make_app(template_folder=os.path.join(HERE, "views")):
	app = Flask(__name__, template_folder=template_folder)

	@app.route("/", defaults={"req_path": ""})
	@app.route("/<path:req_path>")
	def browse(req_path=""):
		base = os.environ.get("FILE_DIR") or DEFAULT_BASE
		base = os.path.abspath(base)

		target_path = os.path.abspath(os.path.join(base, req_path))
		if not target_path.startswith(base):
			abort(403)
		if os.path.isfile(target_path):
			directory = os.path.dirname(target_path)
			file = os.path.basename(target_path)
			return send_from_directory(directory, file, as_attachment=True)

		entries = []
		try:
			with os.scandir(target_path) as it:
				for e in it:
					if e.is_dir():
						child_dir = os.path.join(target_path, e.name)
						if dir_contains_hide(child_dir):
							continue
					stat = e.stat()
					rel_path = os.path.normpath(os.path.join(req_path, e.name)).replace('\\', '/')
					entries.append({
						"name": e.name,
						"display": e.name + ("/" if e.is_dir() else ""),
						"rel_path": rel_path,
						"is_dir": e.is_dir(),
						"mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
						"size": "—" if e.is_dir() else sizeof_fmt(stat.st_size),
						"type": map_type(e.is_dir(), e.name),
					})
		except FileNotFoundError:
			abort(404)

		entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

		parent = None
		if os.path.abspath(target_path) != base:
			parent = os.path.normpath(os.path.join(req_path, "..")).replace('\\', '/')
			if parent == ".":
				parent = ""

		return render_template("files.html", entries=entries, parent=parent, current_path=req_path)

	return app


if __name__ == "__main__":
	import argparse

	p = argparse.ArgumentParser(description="Tiny file server (Flask) - renders `src/views/files.html` template")
	p.add_argument("--dir", "-d", default=os.environ.get("FILE_DIR") or DEFAULT_BASE, help="Directory to serve")
	p.add_argument("--host", "-H", default="0.0.0.0")
	p.add_argument("--port", "-p", type=int, default=8000)
	args = p.parse_args()

	# update DEFAULT_BASE for runtime
	DEFAULT_BASE = os.path.abspath(args.dir)
	app = make_app()
	app.config["BASE_DIR"] = DEFAULT_BASE
	app.run(host=args.host, port=args.port, debug=True)

