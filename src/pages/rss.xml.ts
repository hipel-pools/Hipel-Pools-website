// RSS feed for the main blog (blog.hipelpools.ca/rss.xml). Removed from the main-site build by postbuild.
import { posts, SITE } from '../lib/content';
import { rssFeed } from '../lib/rss';

export function GET() {
  return rssFeed('Hipel Pools Blog', SITE.blogHost, posts.filter((p) => p.blog === 'main'));
}
