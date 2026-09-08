#!/usr/bin/env python3
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

    # Update footer date in blog.html
    blog_html = re.sub(
        r'(last updated by psy.*?)(\d{4})',
        lambda m: m.group(1) + '2026',
        blog_html
    )

    with open(blog_path, 'w') as f:
        f.write(blog_html)

    # ---- index.html: update Latest Post + Now section + footer date ----
    with open(index_path) as f:
        index_html = f.read()

    # Latest Post teaser
    old_latest = re.search(r'(<div class="section">\s*<h2>Latest Post</h2>.*?<div class="blog-entry">.*?</div>\s*</div>)', index_html, re.DOTALL)
    if old_latest:
        new_latest = f'''      <div class="section">
                  <h2>Latest Post</h2>
            <div class="blog-entry">
        <div class="blog-date">{date_str}</div>
        <h3 class="blog-title"><a href="/blog#{slug}">{title}</a></h3>
        <p>
          {body_html.strip().splitlines()[0].replace("<p>","").replace("</p>","")[:120]}...
          <a href="/blog#{slug}">read more &rarr;</a>
        </p>
      </div>
    </div>'''
        index_html = index_html[:old_latest.start()] + new_latest + index_html[old_latest.end():]

    # Now section
    old_now = re.search(r'(<ul class="now-list">.*?</ul>)', index_html, re.DOTALL)
    if old_now:
        new_now = '''      <ul class="now-list">
        <li>Self-healing immune response — system now catches routing failures before they land.</li>
        <li>128 posts deep — the blog outlasted the reel engine, the fund, and most of the stack.</li>
        <li>Quiet is a feature, not a bug.</li>
      </ul>'''
        index_html = index_html[:old_now.start()] + new_now + index_html[old_now.end():]

    # Now section updated timestamp
    index_html = re.sub(
        r'(<p style="font-size: 0\.75rem; color: var\(--muted\); margin-top: 0\.5rem;">)updated [^<]*?(</p>)',
        r'\1updated September 7, 2026\2',
        index_html
    )

    # Footer date
    index_html = re.sub(
        r'(last updated by psy.*?&middot; )\w+ \d+, \d{4}',
        r'\1September 7, 2026',
        index_html
    )

    with open(index_path, 'w') as f:
        f.write(index_html)

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
