from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import click
from openai import OpenAI, OpenAIError

DEFAULT_MODEL = "gpt-4o"


@click.group(context_settings={"show_default": True})
def main() -> None:
    """rename-movies の CLI エントリーポイント。"""


@main.command(name="rename")
@click.argument(
    "videos",
    type=click.Path(path_type=Path, exists=True, dir_okay=False, readable=True),
    nargs=-1,
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="OpenAI API で使用するモデル名。",
)
def rename(videos: tuple[Path, ...], model: str) -> None:
    """複数動画のファイル名候補を提案し、一括でリネームします。"""

    if not videos:
        raise click.ClickException("動画ファイルを1つ以上指定してください。")

    plans: list[tuple[Path, Path, str]] = []
    planned_targets: set[Path] = set()

    for video in videos:
        suggestion = generate_suggestion(video=video, model=model)
        target_path = video.with_name(suggestion)

        click.echo("推奨ファイル名:")
        click.echo(suggestion)

        if target_path.exists():
            raise click.ClickException(f"{target_path} は既に存在します。")
        if target_path in planned_targets:
            raise click.ClickException(
                f"提案結果が重複しました: {target_path.name}。プロンプト条件を調整してください。"
            )

        plans.append((video, target_path, suggestion))
        planned_targets.add(target_path)
        click.echo("-" * 40)

    click.echo("リネームプレビュー:")
    for source, target, _ in plans:
        click.echo(f"{source.name} -> {target.name}")

    if click.confirm("上記のリネームをまとめて適用しますか？", default=True):
        for source, target, _ in plans:
            source.rename(target)
            click.echo(f"リネーム完了: {target}")
    else:
        click.echo("リネームをキャンセルしました。")


def generate_suggestion(*, video: Path, model: str) -> str:
    click.echo(f"動画: {video}")
    with tempfile.TemporaryDirectory(prefix=f"rename-movies-{video.stem}-") as tmpdir:
        frame_file = Path(tmpdir) / f"{video.stem}_frame0.jpg"
        extract_first_frame(video, frame_file)
        click.echo(f"抽出した画像(一時ファイル): {frame_file}")

        suggestion = request_video_filename(
            model=model, video_path=video, image_path=frame_file
        )
    return suggestion


def extract_first_frame(video_path: Path, output_path: Path) -> Path:
    """ffmpeg を使って動画の1フレーム目をJPEGで書き出す。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise click.ClickException(
            "ffmpeg が見つかりません。インストールして PATH に追加してください。"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"ffmpeg 実行に失敗しました: {exc.stderr.decode('utf-8', 'ignore')}"
        ) from exc

    return output_path


def request_video_filename(*, model: str, video_path: Path, image_path: Path) -> str:
    """OpenAI API を呼び出して動画名の候補を取得する。"""

    api_key = os.environ.get("OPENAI_API_KEY_FOR_RENAME_MOVIE")
    if not api_key:
        raise click.ClickException(
            "環境変数 OPENAI_API_KEY_FOR_RENAME_MOVIE が設定されていません。"
        )

    client = OpenAI(api_key=api_key)
    image_bytes = image_path.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    mime_type = "image/jpeg"
    video_ext = video_path.suffix or ".mp4"
    image_data_url = f"data:{mime_type};base64,{image_b64}"

    system_prompt = (
        "あなたは動画ライブラリを整理するアシスタントです。"
        "入力情報を読み取り、人間が理解しやすく簡潔なファイル名(英数字+ハイフン)を1行で返してください。"
        "拡張子も含めて出力してください。"
    )
    user_prompt = (
        "以下の情報を参考に、動画の内容を想起させる簡潔なファイル名を提案してください。\n"
        f"- 元動画ファイル名: {video_path.name}\n"
        f"- 抽出した画像ファイル名: {image_path.name}\n"
        "命名ルール:\n"
        f"1. 各単語の先頭文字は大文字、残りは小文字で記述し、単語と単語の間には必ず半角スペースを入れ、最後に {video_ext} を付けること。\n"
        "2. 4語以内に収めること。\n"
        "3. シーンや登場人物など、画像や元名から推測できる要素を盛り込むこと。\n"
        "4. 出力は1行のみ。余計な説明は不要。\n"
    )

    input_payload: Any = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": user_prompt},
                {
                    "type": "input_image",
                    "image_url": image_data_url,
                },
            ],
        },
    ]

    try:
        response: Any = client.responses.create(
            model=model,
            input=input_payload,
            max_output_tokens=100,
        )
    except OpenAIError as exc:
        raise click.ClickException(
            f"OpenAI API の呼び出しに失敗しました: {exc}"
        ) from exc

    message = _extract_output_text(response)
    if not message:
        raise click.ClickException(
            "OpenAI API からテキスト応答が取得できませんでした。"
        )
    return message.strip()


def _extract_output_text(response: Any) -> str:
    """Responses API の応答から output_text ブロックを取り出す。"""

    outputs = _get_attr(response, "output") or []
    texts: list[str] = []

    for item in outputs:
        content = _get_attr(item, "content") or []
        for block in content:
            block_type = _get_attr(block, "type")
            if block_type != "output_text":
                continue
            text_value = _get_attr(block, "text")
            if text_value:
                texts.append(str(text_value))

    return "\n".join(texts)


def _get_attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


if __name__ == "__main__":
    main()
