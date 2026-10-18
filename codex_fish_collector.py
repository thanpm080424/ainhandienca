"""Thu thập ảnh cá cảnh từ Commons, iNaturalist và DuckDuckGo Images.

Tác giả đồ án: Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428).
Ảnh được lọc bằng Pillow, lưu riêng với tiền tố codex_ và ghi nguồn/license
vào dataset_ca/codex_fish_collector_manifest.jsonl.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import io
import json
import os
import random
import re
import socket
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image, ImageFile, UnidentifiedImageError

ImageFile.LOAD_TRUNCATED_IMAGES = False

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_DIR = BASE_DIR / "dataset_ca"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ACCEPTED_INAT_LICENSES = {
    "cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa",
}
BLOCKED_TITLE_WORDS = re.compile(
    r"\b(logo|icon|clip.?art|vector|diagram|symbol|sticker|banner|watermark|emblem)\b", re.I
)
USER_AGENT = "CodexFishCollector/1.0 (educational fish image dataset; contact: project maintainers)"

# Từ khóa theo danh mục lớp trong predict_fish.py; không import module đó vì
# import model YOLO sẽ làm CLI nặng và có thể tự tải weights.
SPECIES_QUERIES: dict[str, tuple[str, ...]] = {
    "ca_ba_duoi": ("Carassius auratus fancy goldfish aquarium", "cá ba đuôi cá vàng hồ cá", "fancy goldfish"),
    "ca_bay_mau": ("Poecilia reticulata fancy guppy aquarium", "Guppy fish male fancy tail", "cá bảy màu full gold"),
    "ca_but_chi": ("Crossocheilus oblongus aquarium", "Crossocheilus siamensis", "cá bút chì ăn rêu"),
    "ca_chuot": ("Corydoras aquarium fish", "Corydoras paleatus", "cá chuột cảnh hồ thủy sinh"),
    "ca_da_quang": ("GloFish tetra fluorescent aquarium", "GloFish Danio rerio", "cá dạ quang thủy sinh"),
    "ca_dia": ("Discus fish Symphysodon aquarium", "Symphysodon aequifasciatus", "cá dĩa bồ câu Blue Diamond"),
    "ca_diec_anh_dao": ("Puntius titteya cherry barb aquarium", "cherry barb fish aquarium", "cá diếc anh đào cảnh"),
    "ca_duoi_kiem": ("Xiphophorus hellerii swordtail aquarium", "swordtail fish aquarium", "cá đuôi kiếm cảnh"),
    "ca_hong_ket": ("blood parrot cichlid aquarium", "hybrid parrot cichlid fish", "cá hồng két thủy sinh"),
    "ca_koi": ("Cyprinus carpio koi pond fish", "Japanese koi fish", "cá chép koi hồ"),
    "ca_la_han": ("Flowerhorn cichlid aquarium", "Kamfa Flowerhorn", "cá la hán thái đỏ"),
    "ca_lau_kieng": ("Hypostomus plecostomus aquarium", "common pleco fish", "cá lau kiếng tỳ bà"),
    "ca_molly": ("Poecilia sphenops molly aquarium", "molly fish aquarium", "cá molly bình tích"),
    "ca_mun": ("Xiphophorus maculatus platy aquarium", "platy fish aquarium", "cá mún platy"),
    "ca_neon": ("Paracheirodon innesi neon tetra aquarium", "neon tetra fish", "cá neon xanh"),
    "ca_rong": ("Scleropages formosus Asian arowana", "Asian arowana aquarium", "cá rồng châu Á"),
    "ca_sac": ("Trichogaster gourami aquarium", "dwarf gourami fish", "cá sặc cảnh thủy sinh"),
    "ca_soc_ngua": ("Danio rerio zebra danio aquarium", "zebrafish aquarium", "cá sọc ngựa"),
    "ca_thien_than": ("Pterophyllum scalare angelfish aquarium", "freshwater angelfish", "cá thần tiên nước ngọt"),
    "ca_xiem": ("Betta splendens Siamese fighting fish", "Betta fish aquarium", "cá xiêm betta"),
}

# iNaturalist nhận taxon cụ thể hiệu quả hơn cụm từ tìm kiếm hình ảnh.
INAT_TAXA: dict[str, tuple[str, ...]] = {
    "ca_ba_duoi": ("Carassius auratus",), "ca_bay_mau": ("Poecilia reticulata",),
    "ca_but_chi": ("Crossocheilus oblongus",), "ca_chuot": ("Corydoras",),
    "ca_da_quang": ("Gymnocorymbus ternetzi", "Danio rerio"), "ca_dia": ("Symphysodon",),
    "ca_diec_anh_dao": ("Puntius titteya",), "ca_duoi_kiem": ("Xiphophorus hellerii",),
    "ca_hong_ket": ("Amphilophus citrinellus",), "ca_koi": ("Cyprinus carpio",),
    "ca_la_han": ("Flowerhorn",), "ca_lau_kieng": ("Hypostomus plecostomus",),
    "ca_molly": ("Poecilia sphenops",), "ca_mun": ("Xiphophorus maculatus",),
    "ca_neon": ("Paracheirodon innesi",), "ca_rong": ("Scleropages formosus",),
    "ca_sac": ("Trichogaster",), "ca_soc_ngua": ("Danio rerio",),
    "ca_thien_than": ("Pterophyllum scalare",), "ca_xiem": ("Betta splendens",),
}

# Các loài được nêu là thiếu nhiều ảnh trong brief được ưu tiên khi số lượng bằng nhau.
PRIORITY_SPECIES = ["ca_but_chi", "ca_da_quang", "ca_dia", "ca_bay_mau", "ca_la_han"]


@dataclass(frozen=True)
class Candidate:
    url: str
    source: str
    query: str
    title: str = ""
    page_url: str = ""
    license: str = "unknown"
    attribution: str = ""


class Collector:
    def __init__(self, dataset_dir: Path, workers: int = 8, allow_unlicensed: bool = False):
        self.dataset_dir = dataset_dir.resolve()
        self.workers = max(1, min(16, workers))
        self.allow_unlicensed = allow_unlicensed
        self.lock = threading.Lock()
        self.manifest_lock = threading.Lock()
        self.hashes: dict[str, set[str]] = {}
        self.indices: dict[str, int] = {}
        self.reserved_counts: dict[str, int] = {}
        self.manifest_path = self.dataset_dir / "codex_fish_collector_manifest.jsonl"

    def _existing_hashes(self, species: str) -> set[str]:
        target = self.dataset_dir / species
        known: set[str] = set()
        if target.is_dir():
            for path in target.rglob("*"):
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                    try:
                        digest = hashlib.sha256(path.read_bytes()).hexdigest()
                        known.add(digest)
                    except OSError as exc:
                        print(f"[WARN] Không đọc được ảnh hiện có {path}: {exc}", file=sys.stderr)
        self.hashes[species] = known
        self.indices[species] = 1
        return known

    def count_images(self, species: str) -> int:
        folder = self.dataset_dir / species
        if not folder.is_dir():
            return 0
        return sum(1 for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)

    @staticmethod
    @lru_cache(maxsize=512)
    def _safe_https_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                return False
            host = parsed.hostname.lower().rstrip(".")
            if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
                return False
            try:
                address = ipaddress.ip_address(host)
                return address.is_global
            except ValueError:
                # Reject obvious local/internal hostnames; API and image hosts are public DNS names.
                if "." not in host or host.endswith((".internal", ".lan", ".home")):
                    return False
                try:
                    resolved = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
                    if not resolved or any(not ipaddress.ip_address(item[4][0]).is_global for item in resolved):
                        return False
                except OSError:
                    return False
            return True
        except (TypeError, ValueError):
            return False

    def _get(self, url: str, *, params: dict[str, Any] | None = None,
             stream: bool = False, max_redirects: int = 4) -> requests.Response:
        """GET có giới hạn redirect; kiểm tra URL công khai trước mỗi request."""
        current_url = url
        current_params = params
        for _ in range(max_redirects + 1):
            if not self._safe_https_url(current_url):
                raise ValueError(f"Từ chối URL không an toàn: {current_url}")
            response = requests.get(current_url, params=current_params,
                                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                                    timeout=(8, 25), stream=stream, allow_redirects=False)
            current_params = None
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise requests.RequestException("Redirect không có Location.")
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            return response
        raise requests.TooManyRedirects(f"Quá nhiều redirect khi tải {url}")

    @staticmethod
    def _metadata_text(value: Any) -> str:
        if isinstance(value, dict):
            value = value.get("value", "")
        return html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).strip()

    def search_commons(self, query: str, limit: int) -> list[Candidate]:
        api = "https://commons.wikimedia.org/w/api.php"
        candidates: list[Candidate] = []
        continuation: dict[str, Any] = {}
        for _ in range(3):
            params = {
                "action": "query", "format": "json", "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6,
                "gsrlimit": min(50, max(10, limit)), "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600,
                **continuation,
            }
            try:
                response = self._get(api, params=params)
                data = response.json()
            except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                print(f"[WARN] Wikimedia query lỗi ({query}): {exc}", file=sys.stderr)
                break
            pages = (data.get("query") or {}).get("pages") or {}
            for page in pages.values():
                info = (page.get("imageinfo") or [{}])[0]
                metadata = info.get("extmetadata") or {}
                license_name = self._metadata_text(metadata.get("LicenseShortName"))
                if not self._is_acceptable_license(license_name):
                    continue
                candidates.append(Candidate(
                    url=info.get("thumburl") or info.get("url", ""), source="Wikimedia Commons",
                    query=query, title=page.get("title", ""), page_url=info.get("descriptionurl", ""),
                    license=license_name,
                    attribution=self._metadata_text(metadata.get("Artist") or metadata.get("Credit")),
                ))
                if len(candidates) >= limit:
                    return candidates
            continuation = data.get("continue") or {}
            if not continuation:
                break
        return candidates

    @staticmethod
    def _is_acceptable_license(license_name: str) -> bool:
        normalized = license_name.strip().lower().replace(" ", "-")
        if not normalized:
            return False
        return bool(re.fullmatch(r"cc0(?:-[0-9.]+)?|pd|public-domain|cc-by(?:-[0-9.]+)?|cc-by-sa(?:-[0-9.]+)?", normalized)
                    or "public domain" in license_name.lower())

    def search_inaturalist(self, query: str, limit: int) -> list[Candidate]:
        api = "https://api.inaturalist.org/v1/observations"
        candidates: list[Candidate] = []
        for page in range(1, 4):
            params = {
                "taxon_name": query, "photos": "true", "quality_grade": "research",
                "per_page": min(200, max(20, limit)), "page": page,
                "order": "desc", "order_by": "votes",
            }
            try:
                response = self._get(api, params=params)
                data = response.json()
            except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                print(f"[WARN] iNaturalist query lỗi ({query}): {exc}", file=sys.stderr)
                break
            observations = data.get("results") or []
            for observation in observations:
                for photo in observation.get("photos") or []:
                    license_code = str(photo.get("license_code") or "").lower()
                    if license_code not in ACCEPTED_INAT_LICENSES:
                        continue
                    url = str(photo.get("url") or "")
                    if not url:
                        continue
                    url = re.sub(r"/(square|small|medium|original)\.", "/large.", url)
                    candidates.append(Candidate(
                        url=url, source="iNaturalist", query=query,
                        title=observation.get("species_guess") or observation.get("taxon", {}).get("name", ""),
                        page_url=f"https://www.inaturalist.org/observations/{observation.get('id', '')}",
                        license=license_code,
                        attribution=str(observation.get("user", {}).get("login", "")),
                    ))
                    if len(candidates) >= limit:
                        return candidates
            if len(observations) < params["per_page"]:
                break
        return candidates

    def search_duckduckgo(self, query: str, limit: int) -> list[Candidate]:
        """Search DDG via current ddgs package, then legacy duckduckgo_search."""
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore[no-redef]
        except ImportError:
            print("[WARN] Bỏ qua DuckDuckGo: cài package tùy chọn bằng `pip install ddgs`.", file=sys.stderr)
            return []
        try:
            results = DDGS(timeout=20).images(query, max_results=limit)
            return [Candidate(url=item.get("image", ""), source="DuckDuckGo Images", query=query,
                              title=item.get("title", ""), page_url=item.get("url", ""),
                              license="unknown", attribution=item.get("source", ""))
                    for item in results if item.get("image")]
        except Exception as exc:
            print(f"[WARN] DuckDuckGo query lỗi ({query}): {exc}", file=sys.stderr)
            return []

    def gather_candidates(self, species: str, needed: int, sources: set[str]) -> list[Candidate]:
        queries = SPECIES_QUERIES[species]
        per_query = min(100, max(30, needed))
        work: list[tuple[str, str]] = []
        for query in queries[:3]:
            for source in ("commons", "ddg"):
                if source in sources:
                    work.append((source, query))
        if "inat" in sources:
            work.extend(("inat", taxon) for taxon in INAT_TAXA[species])
        all_candidates: list[Candidate] = []
        with ThreadPoolExecutor(max_workers=min(self.workers, max(1, len(work)))) as executor:
            futures = []
            for source, query in work:
                if source == "commons":
                    futures.append(executor.submit(self.search_commons, query, per_query))
                elif source == "inat":
                    futures.append(executor.submit(self.search_inaturalist, query, per_query))
                else:
                    futures.append(executor.submit(self.search_duckduckgo, query, per_query))
            for future in as_completed(futures):
                try:
                    all_candidates.extend(future.result())
                except Exception as exc:
                    print(f"[WARN] Tìm kiếm ảnh lỗi: {exc}", file=sys.stderr)
        # Trộn nguồn, rồi bỏ URL lặp để đa dạng dữ liệu.
        deduplicated: dict[str, Candidate] = {}
        for candidate in all_candidates:
            canonical = candidate.url.split("?", 1)[0].lower()
            if canonical and canonical not in deduplicated:
                deduplicated[canonical] = candidate
        candidates = list(deduplicated.values())
        random.Random(species + str(int(time.time() // 3600))).shuffle(candidates)
        return candidates

    @staticmethod
    def _read_image(candidate: Candidate, allow_unlicensed: bool) -> tuple[bytes, Image.Image] | None:
        if candidate.license == "unknown" and not allow_unlicensed:
            return None
        if BLOCKED_TITLE_WORDS.search(candidate.title):
            return None
        if not Collector._safe_https_url(candidate.url):
            return None
        try:
            # Hàm gọi này chạy trong worker; tạo session cục bộ để tránh chia sẻ
            # trạng thái requests.Session giữa các thread.
            with requests.Session() as session:
                session.headers.update({"User-Agent": USER_AGENT})
                current = candidate.url
                for _ in range(5):
                    if not Collector._safe_https_url(current):
                        return None
                    response = session.get(current, timeout=(8, 25), stream=True, allow_redirects=False)
                    if response.is_redirect or response.is_permanent_redirect:
                        location = response.headers.get("Location")
                        response.close()
                        if not location:
                            return None
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
                    declared_size = int(response.headers.get("Content-Length") or 0)
                    if declared_size and declared_size < 15 * 1024:
                        response.close()
                        return None
                    if declared_size > 20 * 1024 * 1024:
                        response.close()
                        return None
                    chunks = bytearray()
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            chunks.extend(chunk)
                            if len(chunks) > 20 * 1024 * 1024:
                                response.close()
                                return None
                    response.close()
                    raw = bytes(chunks)
                    if len(raw) < 15 * 1024 or (content_type and not content_type.startswith("image/")):
                        return None
                    try:
                        with Image.open(io.BytesIO(raw)) as check:
                            if check.format not in {"JPEG", "PNG", "WEBP"}:
                                return None
                            check.verify()
                        with Image.open(io.BytesIO(raw)) as image:
                            if image.width < 350 or image.height < 350:
                                return None
                            ratio = image.width / image.height
                            if not 0.45 <= ratio <= 2.4:
                                return None
                            if image.mode in {"RGBA", "LA"}:
                                alpha = image.getchannel("A")
                                transparent_ratio = sum(alpha.histogram()[:250]) / (image.width * image.height)
                                if transparent_ratio > 0.45:
                                    return None
                            image.load()
                            return raw, image.convert("RGB")
                    except (UnidentifiedImageError, OSError, ValueError):
                        return None
                return None
        except (requests.RequestException, OSError, ValueError):
            return None

    def _allocate_path(self, species: str) -> Path:
        folder = self.dataset_dir / species
        folder.mkdir(parents=True, exist_ok=True)
        while True:
            index = self.indices.get(species, 1)
            self.indices[species] = index + 1
            timestamp = int(time.time())
            path = folder / f"codex_{species}_{timestamp}_{index:02d}.jpg"
            if not path.exists():
                return path

    def _save_candidate(self, species: str, candidate: Candidate, limit: int) -> tuple[bool, str]:
        with self.lock:
            if self.reserved_counts.get(species, 0) >= limit:
                return False, "limit_reached"
        result = self._read_image(candidate, self.allow_unlicensed)
        if result is None:
            return False, "quality/license/url"
        raw, image = result
        encoded = io.BytesIO()
        image.save(encoded, format="JPEG", quality=92, optimize=True)
        converted = encoded.getvalue()
        if len(converted) < 15 * 1024:
            return False, "converted_small"
        digest = hashlib.sha256(converted).hexdigest()
        with self.lock:
            if digest in self.hashes.setdefault(species, set()):
                return False, "duplicate"
            if self.reserved_counts.get(species, 0) >= limit:
                return False, "limit_reached"
            self.reserved_counts[species] = self.reserved_counts.get(species, 0) + 1
            self.hashes[species].add(digest)
            destination = self._allocate_path(species)

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(prefix="codex_", suffix=".jpg.tmp", dir=destination.parent,
                                             delete=False) as handle:
                temporary_path = Path(handle.name)
                handle.write(converted)
            os.replace(temporary_path, destination)
            record = {
                "file": str(destination.relative_to(self.dataset_dir)),
                "species_key": species,
                "source": candidate.source,
                "source_page": candidate.page_url,
                "image_url": candidate.url,
                "query": candidate.query,
                "title": candidate.title,
                "license": candidate.license,
                "attribution": candidate.attribution,
                "sha256_jpg": digest,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            with self.manifest_lock:
                with self.manifest_path.open("a", encoding="utf-8") as manifest:
                    manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
            return True, "saved"
        except Exception:
            with self.lock:
                self.hashes.get(species, set()).discard(digest)
                self.reserved_counts[species] = max(0, self.reserved_counts.get(species, 1) - 1)
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        finally:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)

    def collect(self, species: str, limit: int, sources: set[str]) -> int:
        if species not in SPECIES_QUERIES:
            raise ValueError(f"Loài không được hỗ trợ: {species}. Chọn một trong: {', '.join(SPECIES_QUERIES)}")
        if limit <= 0:
            return 0
        if species not in self.hashes:
            self._existing_hashes(species)
        print(f"\n[{species}] Mục tiêu: tải thêm {limit} ảnh; nguồn: {', '.join(sorted(sources))}")
        candidates = self.gather_candidates(species, limit, sources)
        if not candidates:
            print(f"[{species}] Không tìm thấy ảnh ứng viên.")
            return 0
        print(f"[{species}] Có {len(candidates)} URL ứng viên; bắt đầu tải tối đa {self.workers} luồng.")
        saved = 0
        skipped: dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self._save_candidate, species, candidate, limit): candidate for candidate in candidates}
            for future in as_completed(futures):
                try:
                    accepted, reason = future.result()
                except Exception as exc:
                    skipped["error"] = skipped.get("error", 0) + 1
                    print(f"[{species}] Lỗi lưu ảnh: {exc}", file=sys.stderr)
                    continue
                if accepted:
                    saved += 1
                    print(f"[{species}] Đã lưu {saved}/{limit}: {futures[future].title or futures[future].url[:80]}")
                    if saved >= limit:
                        for pending in futures:
                            pending.cancel()
                        break
                else:
                    skipped[reason] = skipped.get(reason, 0) + 1
        print(f"[{species}] Hoàn tất: {saved}/{limit} ảnh; bỏ qua {sum(skipped.values())} ứng viên {skipped}.")
        return saved


def count_species_images(dataset_dir: Path) -> dict[str, int]:
    """Đếm file ảnh theo đuôi phổ biến trong các thư mục loài đã khai báo."""
    counts = {}
    for species in SPECIES_QUERIES:
        folder = dataset_dir / species
        counts[species] = sum(1 for path in folder.rglob("*")
                              if folder.is_dir() and path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thu thập ảnh cá cảnh từ Commons, iNaturalist và DuckDuckGo.")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--species", choices=sorted(SPECIES_QUERIES), help="Mã lớp cần thu thập.")
    choice.add_argument("--auto-fill", action="store_true", help="Ưu tiên bù các lớp đang thiếu so với --target.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Số ảnh mới cho --species; với --auto-fill là mức trần bổ sung mỗi lớp.")
    parser.add_argument("--target", type=int, default=500, help="Mốc ảnh mỗi loài khi dùng --auto-fill (mặc định 500).")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--workers", type=int, default=8, help="Số luồng tải đồng thời (1..16).")
    parser.add_argument("--sources", default="commons,inaturalist,ddg",
                        help="Danh sách nguồn, phân cách dấu phẩy: commons,inaturalist,ddg.")
    parser.add_argument("--allow-unlicensed", action="store_true",
                        help="Cho phép ảnh DDG không có metadata giấy phép rõ ràng; hãy kiểm tra quyền sử dụng thủ công.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        print("--limit phải lớn hơn 0.", file=sys.stderr)
        return 2
    if args.target <= 0:
        print("--target phải lớn hơn 0.", file=sys.stderr)
        return 2
    if not 1 <= args.workers <= 16:
        print("--workers cần nằm trong 1..16.", file=sys.stderr)
        return 2
    aliases = {"inaturalist": "inat"}
    sources = {aliases.get(item.strip().lower(), item.strip().lower())
               for item in args.sources.split(",") if item.strip()}
    invalid_sources = sources - {"commons", "inat", "ddg"}
    if invalid_sources or not sources:
        print(f"Nguồn không hợp lệ: {', '.join(sorted(invalid_sources)) or '(rỗng)'}", file=sys.stderr)
        return 2

    dataset_dir = args.dataset_dir.expanduser().resolve()
    dataset_dir.mkdir(parents=True, exist_ok=True)
    collector = Collector(dataset_dir, args.workers, args.allow_unlicensed)
    if args.species:
        limit = args.limit if args.limit is not None else 100
        collector.collect(args.species, limit, sources)
    else:
        counts = count_species_images(dataset_dir)
        priority_order = {species: index for index, species in enumerate(PRIORITY_SPECIES)}
        deficient = [(species, max(0, args.target - count)) for species, count in counts.items()]
        deficient = [(species, deficit) for species, deficit in deficient if deficit > 0]
        deficient.sort(key=lambda item: (-item[1], priority_order.get(item[0], len(priority_order)), item[0]))
        if args.limit is not None:
            deficient = [(species, min(deficit, args.limit)) for species, deficit in deficient]
        if not deficient:
            print(f"Tất cả lớp đã đạt mốc {args.target} ảnh.")
            return 0
        print("Ưu tiên bổ sung theo số ảnh thiếu:")
        for species, deficit in deficient:
            print(f"  {species}: hiện có {counts[species]}, thiếu {deficit}")
        for species, deficit in deficient:
            collector.collect(species, deficit, sources)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nĐã dừng theo yêu cầu người dùng.", file=sys.stderr)
        raise SystemExit(130)
