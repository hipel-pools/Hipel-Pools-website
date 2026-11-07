// RSS feed for the Academy blog (blog.hipelpools.ca/academy/rss.xml).
import { posts, SITE } from '../../lib/content';
import { rssFeed } from '../../lib/rss';

export function GET() {
  return rssFeed('Hipel Pools - Academy', SITE.blogHost + '/academy', posts.filter((p) => p.blog === 'academy'));
}
