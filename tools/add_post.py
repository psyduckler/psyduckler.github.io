#!/usr/bin/env python3
"""Add a blog post. Run from repo root:
  python3 tools/add_post.py blog.html index.html feed.xml <slug> "<Title>" "<Month D, YYYY>" "<RFC822 date>" "<p>body html</p>"
Inserts into blog.html and feed.xml, then rebuilds index.html via tools/build.py.
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

    # ---- blog.html: add new entry after <div class="section">...<h2>Blog</h2> ----
    with open(blog_path) as f:
        blog_html = f.read()

    new_blog_entry = f'''      <div class="blog-entry" id="{slug}">
        <div class="blog-date">{date_str}</div>
        <h3 class="blog-title">{title}</h3>
{body_html}
      </div>

'''

    blog_html = re.sub(
        r'(<div class="section">\s*<h2>Blog</h2>\s*)',
        r'\1' + new_blog_entry,
        blog_html,
        count=1
    )


    with open(blog_path, 'w') as f:
        f.write(blog_html)

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
