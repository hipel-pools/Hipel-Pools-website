/**
 * Cloudflare Pages Function: POST /api/form
 *
 * Replaces HubSpot form handling. Emails each submission (with any uploaded file attached)
 * to the business using Resend (https://resend.com – free tier: 3,000 emails/month).
 *
 * Environment variables (Cloudflare Pages > Settings > Environment variables):
 *   RESEND_API_KEY   required  – API key from resend.com (mark as "Encrypt")
 *   FORM_TO          optional  – where leads go (default sales@hipelpools.ca)
 *   FORM_FROM        optional  – verified sender, e.g. "Hipel Pools Website <website@hipelpools.ca>"
 */
interface Env { RESEND_API_KEY?: string; FORM_TO?: string; FORM_FROM?: string }

const THANK_YOU: Record<string, string> = {
  quote: '/thankyou-for-requesting-a-quote',
  contact: '/company/contact-us?submitted=1',
};
const LABELS: Record<string, string> = {
  firstname: 'First Name', lastname: 'Last Name', email: 'Email', mobilephone: 'Mobile Phone', phone: 'Phone',
  address: 'Street Address', city: 'City', state: 'Province', services: 'Services Interested In',
  heard: 'How Did You Hear About Us', message: 'Message / Project Details', page: 'Submitted From',
};
const MAX_FILE = 10 * 1024 * 1024;

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));

function b64(buf: ArrayBuffer) {
  let s = '';
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  const wantsJson = (request.headers.get('accept') || '').includes('application/json');
  const reply = (ok: boolean, kind: string, message: string, status = ok ? 200 : 400) => {
    if (wantsJson) return Response.json({ ok, message, redirect: ok ? THANK_YOU[kind] : undefined }, { status });
    if (ok) return Response.redirect(new URL(THANK_YOU[kind] || '/', request.url).toString(), 303);
    return new Response(`<p>${esc(message)}</p><p><a href="javascript:history.back()">Go back</a></p>`, {
      status, headers: { 'content-type': 'text/html; charset=utf-8' },
    });
  };

  let data: FormData;
  try { data = await request.formData(); } catch { return reply(false, 'quote', 'Invalid submission.'); }
  const kind = String(data.get('form') || 'quote') === 'contact' ? 'contact' : 'quote';

  // Spam honeypot: real people never see this field.
  if (String(data.get('company_website') || '').trim()) return reply(true, kind, 'Thanks!');

  const required = kind === 'quote'
    ? ['firstname', 'lastname', 'email', 'address', 'city', 'state', 'heard', 'message']
    : ['firstname', 'lastname', 'email', 'message'];
  for (const f of required) if (!String(data.get(f) || '').trim()) return reply(false, kind, `Please fill in ${LABELS[f] || f}.`);
  const email = String(data.get('email'));
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return reply(false, kind, 'Please enter a valid email address.');

  if (!env.RESEND_API_KEY) return reply(false, kind, 'The form is not configured yet. Please call (519)-997-2434 or email sales@hipelpools.ca.', 500);

  const rows: string[] = [];
  for (const key of Object.keys(LABELS)) {
    const vals = data.getAll(key).map(String).filter(Boolean);
    if (vals.length) rows.push(`<tr><th align="left" valign="top">${LABELS[key]}</th><td>${esc(vals.join(', ')).replace(/\n/g, '<br>')}</td></tr>`);
  }
  const attachments: { filename: string; content: string }[] = [];
  const file = data.get('file_upload');
  if (file && typeof file !== 'string' && file.size > 0) {
    if (file.size > MAX_FILE) return reply(false, kind, 'That file is too large (max 10 MB).');
    attachments.push({ filename: file.name || 'upload', content: b64(await file.arrayBuffer()) });
  }
  const name = `${data.get('firstname')} ${data.get('lastname')}`.trim();
  const subject = kind === 'quote' ? `New quote request – ${name}` : `New contact form message – ${name}`;

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: env.FORM_FROM || 'Hipel Pools Website <website@hipelpools.ca>',
      to: (env.FORM_TO || 'sales@hipelpools.ca').split(',').map((s) => s.trim()),
      reply_to: email,
      subject,
      html: `<h2>${esc(subject)}</h2><table cellpadding="6">${rows.join('')}</table>`,
      attachments,
    }),
  });
  if (!res.ok) {
    console.error('Resend error', res.status, await res.text());
    return reply(false, kind, 'Sorry, something went wrong. Please call (519)-997-2434 or email sales@hipelpools.ca.', 502);
  }
  return reply(true, kind, 'Thanks! A representative will be in touch within 1 business day.');
};
