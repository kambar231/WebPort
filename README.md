# KAMBAR — Portfolio

**Live: https://kambar231.github.io/WebPort/**

Portfolio of interactive websites. Any effect. Any animation. Fast iteration.

## Projects

| Project | Live | What it is |
|---|---|---|
| Home | [/](https://kambar231.github.io/WebPort/) | Cloud intro, live project cards, altimeter scroller |
| TERRA | [/terra-museum/](https://kambar231.github.io/WebPort/terra-museum/) | Museum concept — WebGL flow-field, content-aware relief reveal |
| NUMERA | [/numera/](https://kambar231.github.io/WebPort/numera/) | AI-accounting SaaS clone — design tokens, scroll choreography |
| BIAVOLA | [/biavola/](https://kambar231.github.io/WebPort/biavola/) | Wood-fired pizza concept — hover-fed stage, masked imagery |
| ONDA | [/onda-day/](https://kambar231.github.io/WebPort/onda-day/) | Fitness band concept — ambient daylight scroll story |

## Structure

Hand-written HTML/CSS/JS — no framework, no build step. Each project lives in its
own folder as a self-contained `index.html` (clean URLs); shared images are WebP
files under `assets/img/<project>/`.

```
index.html            landing page
404.html              custom not-found page
<project>/index.html  one folder per project
assets/img/<project>/ per-project WebP images
```

**Hosting**: static — currently GitHub Pages; deploys as-is on Vercel or Netlify too.

Contact: kambar231@gmail.com
