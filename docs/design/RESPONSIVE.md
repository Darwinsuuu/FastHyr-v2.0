# Responsive design (mobile first)

Every page — marketing, candidate **and** TA app — is responsive. We build **mobile first**: the base styles are for a phone, and larger layouts are added with `min-width` breakpoints (ADR-020).

The canvas frames are drawn at desktop width (1440 px). They show the **desktop end state**; this document defines how each pattern behaves on smaller screens. If a screen needs a layout not covered here, add it to the screen's task notes and to this doc.

## 1. Breakpoints (Tailwind defaults)
| Name | Min width | Typical device | Layout intent |
|---|---|---|---|
| base | 0 (design for **360 px**) | Phone | Single column, stacked content, full-width actions |
| `sm` | 640 px | Large phone / small tablet portrait | Two-column forms where fields are short |
| `md` | 768 px | Tablet portrait | Tables appear, two-column cards |
| `lg` | 1024 px | Tablet landscape / small laptop | Persistent sidebar, side panels |
| `xl` | 1280 px | Laptop | Full desktop layout from the frames |
| `2xl` | 1536 px | Large desktop | Content max-width; no stretching |

Rules:
- Write base (mobile) classes first, then `sm:` → `2xl:` overrides. Never write desktop styles and "undo" them for mobile.
- Test at **360, 390, 768, 1024, 1280 and 1440 px**.
- **No horizontal page scroll** at any width. Only specific elements (wide tables on small screens, chart x-axes, tab bars) may scroll horizontally inside their own container.
- Page side padding: `space-4` (16 px) on phones, `space-6` from `md`, `space-8`+ from `xl`.
- Content max-width ~1280 px for the TA app and ~1200 px for marketing, centred at `2xl`.

## 2. Touch and input
- Touch targets ≥ **44 × 44 px** on every interactive element (Button `md` height meets this; icon buttons get padding).
- Hover-only information (tooltips such as the fit explanation) must also open on tap/focus.
- Inputs use the right `type`/`inputmode` (email, tel, url, numeric) and `autocomplete` so mobile keyboards fit.
- Text inputs ≥ 16 px font on phones to avoid iOS zoom.
- Respect safe areas (`env(safe-area-inset-*)`) for fixed bottom bars.

## 3. Pattern rules
| Pattern (desktop, from frames) | Phone (base) | Tablet (`md`) | Desktop (`lg`/`xl`) |
|---|---|---|---|
| **App sidebar** | Top bar: menu button, workspace name, user avatar; sidebar opens as a full-height drawer | Same as phone | Persistent sidebar (from `lg`) |
| **Workspace switcher / menus** | Bottom sheet | Popover | Popover |
| **Page header with actions** | Title, then actions full width underneath; secondary actions in an overflow "More" menu | Actions inline, wrap if needed | As designed |
| **Data tables** (pipelines, candidates, members, invoices, ledger, credit usage) | **Card list**: each row becomes a card with the primary field (name/title), status pill, 1–2 key numbers and the row menu | Table with lower-priority columns hidden | Full table |
| **Filters / stage chips / tabs** | Horizontally scrollable chip or tab bar; long filter sets collapse into a "Filter" sheet | Scrollable bar | Full bar |
| **Pagination** | Prev / "Page 2 of 9" / Next; rows-per-page hidden | Compact numbers | As designed |
| **KPI rows** | 2 per row (1 for long values) | 2–4 per row | As designed |
| **Charts** | Full width, fewer axis labels, legend below, horizontal scroll for long time series; tap shows the value | Full width | As designed |
| **Dashboards (Overview, pipeline dashboard, candidates dashboard, credit usage)** | One column, cards in priority order: needs attention → KPIs → funnel → the rest | Two columns | Multi-column grid as designed |
| **Pipeline wizard** | Stepper becomes a compact header "Step 2 of 5 · AI interview" with a progress bar; Back/Continue in a sticky bottom bar | Same, with more room | Vertical stepper on the left as designed |
| **Candidate profile** | Header stacks (name, stage, fit; actions in a sticky bottom bar: Advance / Reject / More); tabs scroll; side cards move below the main content | Two columns where the frame has side cards | As designed |
| **Résumé tab** | PDF viewer full width (pinch zoom), analysis sections below | Side by side from `lg` | As designed |
| **Interview tab** | Player full width, topics as a horizontal chip list, transcript below | Same | Player + topics side by side, transcript as designed |
| **Ask Ava** | Chat full screen; "What Ava can see" moves behind an info button | Chat + side card below | Chat with side cards |
| **Dialogs / modals** | Full-screen sheet with sticky footer buttons | Centred dialog | Centred dialog as designed |
| **Email template editor** | Subject + editor stacked; parameters in a sheet; history behind a button | Editor + collapsible side panel | As designed |
| **Marketing pages** | Single column; hero text before visuals; product tour tabs become a swipeable carousel; nav collapses into a menu | Two-column sections | As designed |
| **Apply page** | Role facts and company card move below the job description; sticky "Apply now" bar at the bottom | Two columns from `lg` | As designed |
| **Interview / device check** | Camera and mic checks stacked; self-view as a small overlay; captions and controls in a bottom panel; topics behind a "What we'll talk about" button | Side-by-side checks | As designed |

## 4. Media and performance on mobile
- Serve responsive images (`next/image` with `sizes`); marketing screenshots have mobile crops where text would be unreadable.
- Candidate pages must stay fast on mid-range phones on 4G: keep JS for apply/interview pages lean and lazy-load charts and heavy components.
- The interview works in portrait and landscape; lock nothing, but lay out for portrait first.
