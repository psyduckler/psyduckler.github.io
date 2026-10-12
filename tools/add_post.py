#!/usr/bin/env python3
"""Add a blog post. Run from repo root:
  python3 tools/add_post.py blog.html index.html feed.xml <slug> "<Title>" "<Month D, YYYY>" "<RFC822 date>" "<p>body html</p>"
Adds the post to data/posts.json and feed.xml, then rebuilds blog.html + index.html via tools/build.py.
(blog_path/index_path args are kept for compatibility and ignored.)
"""
import sys, re

def main():
    blog_path = sys.argv[1]
    index_path = sys.argv[2]
    feed_path = sys.argv[3]
    slug = sys.argv[4]
    title = sys.argv[5]
    date_str = sys.argv[6]
    pub_date_rss = sys.argv[7]
    body_html = sys.argv[8]

    # ---- data/posts.json: prepend; blog.html + index.html are rebuilt by tools/build.py ----
    import json, pathlib as _p
    pj = _p.Path(__file__).resolve().parent.parent / "data" / "posts.json"
    posts = json.loads(pj.read_text())
    posts.insert(0, {"slug": slug, "date": date_str, "title": title, "body": body_html.strip()})
    pj.write_text(json.dumps(posts, indent=1, ensure_ascii=False) + "\n")
    # index.html is regenerated from data/ + the newest blog entry
    import subprocess, pathlib
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("build.py"))], check=True)

    # ---- feed.xml: prepend new item ----
    with open(feed_path) as f:
        feed_xml = f.read()

    excerpt = body_html.strip().replace('<p>','').replace('</p>','')[:200].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    new_feed_item = f'''<item>
      <title>{title}</title>
      <link>https://psyduckler.com/blog#{slug}</link>
      <guid>https://psyduckler.com/blog#{slug}</guid>
      <pubDate>{pub_date_rss}</pubDate>
      <description><![CDATA[{body_html.strip()}]]></description>
    </item>
'''

    feed_xml = feed_xml.replace('<item>', new_feed_item + '<item>', 1)

    with open(feed_path, 'w') as f:
        f.write(feed_xml)

    print("OK", file=sys.stderr)

if __name__ == '__main__':
    main()
