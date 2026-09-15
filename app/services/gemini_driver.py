import asyncio
import logging
import time
from typing import AsyncGenerator, Optional
from playwright.async_api import Locator, Page
from app.config import settings
from app.services.cdp_manager import CDPManager, cdp_manager

logger = logging.getLogger("gemini_cdp.driver")

JS_MONITOR_SCRIPT = """
() => {
    // 1. Detection of generation state via Stop button or progress animations
    const stopBtn = document.querySelector("button[aria-label*='Arrêter'], button[aria-label*='Stop'], button[aria-label*='Interrompre'], button.stop-button, [data-test-id='stop-button'], mat-icon[fonticon='stop']");
    const isStopVisible = !!(stopBtn && (stopBtn.offsetWidth > 0 || stopBtn.offsetHeight > 0));

    const loading = document.querySelector("mat-progress-bar, .loading-dots, [aria-label*='Chargement en cours'], [aria-label*='Generating'], bard-sparkle-animation, .animate-spin");
    const isLoadingVisible = !!(loading && (loading.offsetWidth > 0 || loading.offsetHeight > 0));

    const sendBtn = document.querySelector("button[aria-label*='Envoyer'], button[aria-label*='Send'], button.send-button");
    const isSendEnabled = !!(sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true');

    const is_generating = isStopVisible || isLoadingVisible;

    // 2. Locate response containers
    let responseElements = document.querySelectorAll("model-response");
    if (responseElements.length === 0) {
        responseElements = document.querySelectorAll("div[data-test-id='model-response']");
    }
    const count = responseElements.length;

    let text = "";
    let has_actions = false;

    if (count > 0) {
        const lastResponse = responseElements[count - 1];

        // Vérification des boutons d'actions finaux (copier, partager, etc.)
        const actionBtn = lastResponse.querySelector("button[aria-label*='Copier'], button[aria-label*='Copy'], button[aria-label*='Partager'], button[aria-label*='Share'], message-actions, response-action-bar, .actions-container");
        has_actions = !!(actionBtn && (actionBtn.offsetWidth > 0 || actionBtn.offsetHeight > 0));

        // Extraction propre du contenu
        const contentElem = lastResponse.querySelector("message-content") || lastResponse;
        const clone = contentElem.cloneNode(true);

        // A. Suppression des éléments parasites (chips, citations, boutons, popovers, pieds de tableau)
        const junkSelectors = [
            "source-grounding-carousel",
            "factuality-container",
            "citation-container",
            "sources-carousel",
            "search-grounding-card",
            ".source-grounding",
            ".grounding-sources",
            ".search-chips",
            ".citation-tag",
            ".citation-bubble",
            "[data-test-id*='grounding']",
            "[class*='grounding']",
            "[class*='citation']",
            "button[aria-label*='sources']",
            "mat-chip",
            ".mat-mdc-chip",
            ".table-footer",
            "gem-icon-button",
            "button",
            "gem-popover",
            "mat-icon",
            ".actions-container",
            "message-actions",
            "response-action-bar"
        ];
        junkSelectors.forEach(sel => {
            clone.querySelectorAll(sel).forEach(el => el.remove());
        });

        // B. Traitement des blocs de code <code-block>
        clone.querySelectorAll('code-block').forEach(cb => {
            const langElem = cb.querySelector('.code-block-decoration span');
            let lang = langElem ? langElem.textContent.trim().toLowerCase() : '';
            if (lang.includes('python')) lang = 'python';
            else if (lang === 'c' || lang.includes('c++') || lang.includes('cpp')) lang = lang;
            else if (lang.includes('bash') || lang.includes('shell') || lang.includes('sh')) lang = 'bash';
            else if (lang.includes('javascript') || lang.includes('js')) lang = 'javascript';
            else if (lang.includes('json')) lang = 'json';
            else if (lang.includes('html')) lang = 'html';
            else if (lang.includes('css')) lang = 'css';
            else if (lang.includes('sql')) lang = 'sql';

            const codeElem = cb.querySelector('code, pre');
            const codeText = codeElem ? (codeElem.textContent || '') : '';
            const md = '\\n\\n```' + lang + '\\n' + codeText.replace(/^\\n+|\\n+$/g, '') + '\\n```\\n\\n';
            const tn = document.createTextNode(md);
            if (cb.parentNode) {
                cb.parentNode.replaceChild(tn, cb);
            }
        });

        // Blocs pre orphelins (hors code-block)
        clone.querySelectorAll('pre').forEach(pre => {
            if (!pre.parentNode) return;
            const code = pre.querySelector('code') || pre;
            const codeText = code.textContent || '';
            const md = '\\n\\n```\\n' + codeText.replace(/^\\n+|\\n+$/g, '') + '\\n```\\n\\n';
            const tn = document.createTextNode(md);
            pre.parentNode.replaceChild(tn, pre);
        });

        // C. Traitement des tableaux <table> (visité une seule fois)
        clone.querySelectorAll('table').forEach(table => {
            if (!table.parentNode) return;

            const rows = Array.from(table.querySelectorAll('tr'));
            if (rows.length === 0) return;

            let md = '\\n\\n';
            let headerColCount = 0;

            rows.forEach((r, rowIdx) => {
                const cells = Array.from(r.querySelectorAll('th, td'));
                if (cells.length === 0) return;

                const cellTexts = cells.map(c => {
                    c.querySelectorAll('b, strong').forEach(b => {
                        b.textContent = '**' + b.textContent.trim() + '**';
                    });
                    c.querySelectorAll('code').forEach(cd => {
                        cd.textContent = '`' + cd.textContent.trim() + '`';
                    });
                    c.querySelectorAll('i, em').forEach(em => {
                        em.textContent = '*' + em.textContent.trim() + '*';
                    });
                    let txt = (c.textContent || '').trim().replace(/\\|/g, '/').replace(/\\s+/g, ' ');
                    return txt;
                });

                if (rowIdx === 0) {
                    headerColCount = cellTexts.length;
                    md += '| ' + cellTexts.join(' | ') + ' |\\n';
                    md += '| ' + Array(headerColCount).fill('---').join(' | ') + ' |\\n';
                } else {
                    md += '| ' + cellTexts.join(' | ') + ' |\\n';
                }
            });

            md += '\\n\\n';
            const tn = document.createTextNode(md);
            const target = table.closest('.horizontal-scroll-wrapper') || table.closest('table-block') || table.closest('.table-block-component') || table;
            if (target && target.parentNode) {
                target.parentNode.replaceChild(tn, target);
            }
        });

        // D. Traitement des listes <ul> / <ol>
        clone.querySelectorAll('ul').forEach(ul => {
            if (!ul.parentNode) return;
            const items = Array.from(ul.querySelectorAll(':scope > li'));
            if (items.length > 0) {
                let md = '\\n\\n';
                items.forEach(li => {
                    li.querySelectorAll('b, strong').forEach(b => { b.textContent = '**' + b.textContent.trim() + '**'; });
                    li.querySelectorAll('code').forEach(c => { c.textContent = '`' + c.textContent.trim() + '`'; });
                    li.querySelectorAll('i, em').forEach(em => { em.textContent = '*' + em.textContent.trim() + '*'; });
                    const txt = li.textContent.trim();
                    if (txt) md += '- ' + txt + '\\n';
                });
                md += '\\n';
                const tn = document.createTextNode(md);
                ul.parentNode.replaceChild(tn, ul);
            }
        });

        clone.querySelectorAll('ol').forEach(ol => {
            if (!ol.parentNode) return;
            const items = Array.from(ol.querySelectorAll(':scope > li'));
            if (items.length > 0) {
                let md = '\\n\\n';
                items.forEach((li, idx) => {
                    li.querySelectorAll('b, strong').forEach(b => { b.textContent = '**' + b.textContent.trim() + '**'; });
                    li.querySelectorAll('code').forEach(c => { c.textContent = '`' + c.textContent.trim() + '`'; });
                    li.querySelectorAll('i, em').forEach(em => { em.textContent = '*' + em.textContent.trim() + '*'; });
                    const txt = li.textContent.trim();
                    if (txt) md += (idx + 1) + '. ' + txt + '\\n';
                });
                md += '\\n';
                const tn = document.createTextNode(md);
                ol.parentNode.replaceChild(tn, ol);
            }
        });

        // E. Titres <h1> .. <h6>
        for (let h = 1; h <= 6; h++) {
            clone.querySelectorAll('h' + h).forEach(head => {
                if (!head.parentNode) return;
                const hashes = '#'.repeat(h);
                const tn = document.createTextNode('\\n\\n' + hashes + ' ' + head.textContent.trim() + '\\n\\n');
                head.parentNode.replaceChild(tn, head);
            });
        }

        // F. Paragraphes <p>
        clone.querySelectorAll('p').forEach(p => {
            if (!p.parentNode) return;
            p.querySelectorAll('b, strong').forEach(b => { b.textContent = '**' + b.textContent.trim() + '**'; });
            p.querySelectorAll('code').forEach(c => { c.textContent = '`' + c.textContent.trim() + '`'; });
            p.querySelectorAll('i, em').forEach(em => { em.textContent = '*' + em.textContent.trim() + '*'; });
            const txt = p.textContent.trim();
            const tn = document.createTextNode('\\n\\n' + txt + '\\n\\n');
            p.parentNode.replaceChild(tn, p);
        });

        // Extraction finale et nettoyage
        text = (clone.innerText || clone.textContent || '').trim();
        text = text.split('\\n').map(l => l.trimEnd()).join('\\n');
        text = text.replace(/\\n{3,}/g, '\\n\\n').trim();

        // Nettoyage des préfixes d'interface
        const prefixes = [
            "Recherche sur le Web\\n",
            "Recherche sur le Web...",
            "Recherche sur le Web…",
            "Recherche sur le Web",
            "Gemini a dit\\n",
            "Gemini a dit",
            "Gemini said\\n",
            "Gemini said"
        ];
        for (const p of prefixes) {
            if (text.startsWith(p)) {
                text = text.substring(p.length).trim();
            }
        }
    }

    return {
        count: count,
        is_generating: is_generating,
        is_send_enabled: isSendEnabled,
        has_actions: has_actions,
        text: text
    };
}
"""


class GeminiDriver:
    """High-performance automation driver for the Google Gemini web interface."""

    def __init__(self, manager: CDPManager = cdp_manager) -> None:
        self.manager = manager

    async def _find_input_locator(self, page: Page, timeout_ms: int = 3500) -> Optional[Locator]:
        """Finds the active text input element in the Gemini web interface."""
        for selector in settings.INPUT_SELECTORS:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=timeout_ms):
                    return locator
            except Exception:
                continue

        try:
            locator = page.locator("[contenteditable='true']").first
            if await locator.is_visible(timeout=1000):
                return locator
        except Exception:
            pass

        return None

    async def new_chat(self, page: Page) -> None:
        """Starts a fresh new chat session on Gemini."""
        logger.info("Starting a new chat session on Gemini...")
        clicked = False
        try:
            new_chat_selectors = [
                "a[href='/app']",
                "button[aria-label*='Nouvelle discussion']",
                "button[aria-label*='New chat']",
                "button[aria-label*='Nouvelle']",
                "button[aria-label*='New']",
                "[data-test-id='new-chat-button']",
            ]
            for selector in new_chat_selectors:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=400):
                    await btn.click()
                    clicked = True
                    break
        except Exception:
            clicked = False

        if not clicked:
            await page.goto(settings.GEMINI_URL, wait_until="domcontentloaded")

        await asyncio.sleep(1.2)

        input_elem = await self._find_input_locator(page)
        if input_elem:
            try:
                await input_elem.click()
                await asyncio.sleep(0.2)
            except Exception:
                pass

    async def reset_session(self) -> bool:
        """Explicitly resets the session by creating a new conversation."""
        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()
            await self.new_chat(page)
            return True

    async def _prepare_input(self, page: Page, prompt: str) -> None:
        """Prepares and cleanly inserts the prompt into the input area."""
        input_element = await self._find_input_locator(page)
        if not input_element:
            raise RuntimeError("Could not find prompt input area on Gemini.")

        await input_element.click()
        await asyncio.sleep(0.2)

        # Clear existing input
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.2)

        # Insert text
        await page.keyboard.insert_text(prompt)
        await asyncio.sleep(0.3)

        # Submit via Enter key exclusively to prevent clicking the Stop button
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.6)

    async def _switch_model_if_needed(self, page: Page, target_model: str) -> str:
        """Switches to the requested model if needed."""
        target_clean = target_model.strip().lower()
        btn = page.locator("bard-mode-switcher button, button.input-area-switch, button[aria-label*='sélecteur de mode'], button[aria-label*='mode selector']").first
        if not await btn.is_visible(timeout=800):
            return "Unknown"

        current_text = (await btn.text_content() or "").strip()
        current_clean = current_text.lower()

        # Check if already on the requested model
        if (
            (target_clean in ("pro", "3.1 pro") and "pro" in current_clean)
            or (target_clean in ("flash-lite", "lite", "3.5 flash-lite") and "lite" in current_clean)
            or (target_clean in ("flash", "3.8 flash") and "flash" in current_clean and "lite" not in current_clean)
            or (target_clean in ("thinking", "raisonnement", "étendu", "extended") and ("raisonnement" in current_clean or "étendu" in current_clean or "thinking" in current_clean))
        ):
            return current_text

        logger.info("Switching Gemini model: %s -> %s", current_text, target_model)
        await btn.click()
        await asyncio.sleep(0.4)

        items = page.locator("[role='menuitem'], [role='option'], .mat-mdc-menu-item")
        count = await items.count()
        clicked = False

        for i in range(count):
            item = items.nth(i)
            text = (await item.text_content() or "").lower()
            if target_clean in ("pro", "3.1 pro") and "pro" in text:
                await item.click()
                clicked = True
                break
            elif target_clean in ("flash-lite", "lite", "3.5 flash-lite") and "lite" in text:
                await item.click()
                clicked = True
                break
            elif target_clean in ("flash", "3.8 flash") and "flash" in text and "lite" not in text:
                await item.click()
                clicked = True
                break
            elif target_clean in ("thinking", "raisonnement", "étendu", "extended") and ("raisonnement" in text or "étendu" in text or "thinking" in text):
                await item.click()
                clicked = True
                break

        if not clicked:
            await page.keyboard.press("Escape")
            logger.warning("Requested model '%s' not found in menu selector.", target_model)
            return current_text

        await asyncio.sleep(0.4)
        new_text = (await btn.text_content() or "").strip()
        return new_text

    async def get_current_model(self) -> str:
        """Retrieves the currently selected model name on Gemini."""
        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()
            btn = page.locator("bard-mode-switcher button, button.input-area-switch, button[aria-label*='sélecteur de mode'], button[aria-label*='mode selector']").first
            if await btn.is_visible(timeout=800):
                return (await btn.text_content() or "Flash").strip()
            return "Flash"

    async def get_available_models(self) -> dict:
        """Retrieves the full list of supported models and the active model."""
        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()

            btn = page.locator("bard-mode-switcher button, button.input-area-switch, button[aria-label*='sélecteur de mode'], button[aria-label*='mode selector']").first
            current_model = "Flash"
            models_list = []

            if await btn.is_visible(timeout=800):
                current_model = (await btn.text_content() or "Flash").strip()
                await btn.click()
                await asyncio.sleep(0.4)

                models_raw = await page.evaluate("""
                () => {
                    const items = Array.from(document.querySelectorAll("[role='menuitem'], [role='option'], .mat-mdc-menu-item"));
                    return items.map(el => {
                        const fullText = el.textContent.trim().replace(/\\s+/g, ' ');
                        const isSelected = el.classList.contains('selected') || el.classList.contains('active') || el.getAttribute('aria-selected') === 'true';
                        return {
                            name: fullText,
                            selected: isSelected
                        };
                    });
                }
                """)
                await page.keyboard.press("Escape")

                for m in models_raw:
                    name = m["name"]
                    lower = name.lower()
                    if "lite" in lower:
                        mod_id = "flash-lite"
                    elif "3.1 pro" in lower or lower.startswith("pro") or " pro " in lower:
                        mod_id = "pro"
                    elif "étendu" in lower or "thinking" in lower or lower.startswith("raisonnement"):
                        mod_id = "thinking"
                    elif "flash" in lower:
                        mod_id = "flash"
                    else:
                        mod_id = name.split()[0].lower()

                    models_list.append({
                        "id": mod_id,
                        "name": name,
                        "is_active": m["selected"] or (mod_id in current_model.lower())
                    })

            if not models_list:
                models_list = [
                    {"id": "flash-lite", "name": "3.5 Flash-Lite (Fast responses)", "is_active": "lite" in current_model.lower()},
                    {"id": "flash", "name": "3.8 Flash (Everyday tasks)", "is_active": "flash" in current_model.lower() and "lite" not in current_model.lower()},
                    {"id": "pro", "name": "3.1 Pro (Complex reasoning)", "is_active": "pro" in current_model.lower()},
                    {"id": "thinking", "name": "Extended Thinking", "is_active": "thinking" in current_model.lower()}
                ]

            return {
                "current_model": current_model,
                "models": models_list
            }

    async def set_model(self, model_name: str) -> dict:
        """Switches the active language model."""
        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()
            new_model = await self._switch_model_if_needed(page, model_name)
            return {
                "status": "success",
                "current_model": new_model,
                "message": f"Model switched successfully to: {new_model}"
            }

    async def list_conversations(self) -> list[dict]:
        """Retrieves conversation history saved on the Gemini account."""
        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()

            # Check if sidebar needs to be expanded
            open_btn = page.locator(
                "button[aria-label*='Ouvrir la barre latérale'], button[aria-label*='Open side panel'], button[aria-label*='Ouvrir la barre'], button[aria-label*='Open sidebar'], button[data-test-id='side-nav-sparkle-button'], button[data-test-id='side-nav-button']"
            ).first
            try:
                if await open_btn.is_visible(timeout=1500):
                    logger.info("Collapsed sidebar detected. Clicking to expand panel...")
                    await open_btn.click()
                    await asyncio.sleep(0.8)
            except Exception:
                pass

            convs = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll("gem-nav-list-item a, [data-test-id='conversation'] a, nav a[href*='/app/'], a.gem-nav-list-item, .conversation-item a, a[href*='/app/']"));
                const seen = new Set();
                const results = [];
                links.forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const match = href.match(/\\/app\\/([a-zA-Z0-9]+)/i);
                    if (match) {
                        const id = match[1];
                        if (id && id !== 'new' && !seen.has(id)) {
                            seen.add(id);
                            let title = (a.getAttribute('aria-label') || a.textContent || id).trim().replace(/\\s+/g, ' ');
                            const lower = title.toLowerCase();
                            if (!lower.startsWith("compte google") && !lower.includes("abonnement") && !lower.includes("nouvelle discussion") && !lower.includes("gestion") && !lower.includes("paramètres") && !lower.includes("settings") && !lower.includes("new chat")) {
                                results.push({
                                    id: id,
                                    title: title,
                                    url: 'https://gemini.google.com/app/' + id
                                });
                            }
                        }
                    }
                });
                return results;
            }
            """)
            return convs

    async def load_conversation(self, conversation_id: str) -> dict:
        """Loads a previous conversation into the active session."""
        clean_id = conversation_id.strip()
        if "/app/" in clean_id:
            clean_id = clean_id.split("/app/")[-1].split("/")[0].split("?")[0]

        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()
            target_url = f"https://gemini.google.com/app/{clean_id}"
            logger.info("Loading conversation: %s", target_url)
            await page.goto(target_url, wait_until="domcontentloaded")
            await asyncio.sleep(1.2)
            title = await page.title()
            clean_title = title.replace(" - Google Gemini", "").replace(" - Gemini", "").strip()

            return {
                "status": "success",
                "conversation_id": clean_id,
                "title": clean_title or clean_id,
                "url": target_url,
                "message": f"Conversation '{clean_title}' loaded successfully."
            }

    async def get_usage_metrics(self) -> dict:
        """Retrieves usage limits and quota metrics from https://gemini.google.com/usage."""
        async with self.manager.lock:
            browser = await self.manager.connect()
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            try:
                logger.info("Fetching usage metrics from https://gemini.google.com/usage...")
                await page.goto("https://gemini.google.com/usage", wait_until="domcontentloaded")
                await page.wait_for_selector(".usage-metrics-container, .gxu-items-container", timeout=12000)
                await asyncio.sleep(0.6)

                data = await page.evaluate("""
                () => {
                    const container = document.querySelector('.usage-metrics-container');
                    if (!container) return { error: "Container not found" };

                    const tier = (container.querySelector('.tier-pill')?.textContent || '').trim();
                    const description = (container.querySelector('.usage-metrics-description p')?.textContent || '').trim();

                    // Current usage
                    const currElem = container.querySelector("[data-test-id='gxu-currently'], .gxu-currently");
                    let current_usage = "";
                    let current_reset = "";
                    let current_percent = 0;
                    if (currElem) {
                        const texts = Array.from(currElem.querySelectorAll('p')).map(p => p.textContent.trim());
                        texts.forEach(t => {
                            if (t.includes('%')) current_usage = t;
                            if (t.toLowerCase().includes('réinitialisation') || t.toLowerCase().includes('reinitialisation') || t.toLowerCase().includes('reset')) current_reset = t;
                        });
                        const indicator = currElem.querySelector('.progress-indicator');
                        if (indicator) {
                            const style = indicator.getAttribute('style') || '';
                            const match = style.match(/width:\\s*([0-9.]+)%/i);
                            if (match) current_percent = parseFloat(match[1]);
                        }
                        if (!current_percent && current_usage) {
                            const match = current_usage.match(/([0-9.]+)/);
                            if (match) current_percent = parseFloat(match[1]);
                        }
                    }

                    // Weekly usage
                    const weekElem = container.querySelector("[data-test-id='gxu-weekly'], .gxu-weekly");
                    let weekly_usage = "";
                    let weekly_reset = "";
                    let weekly_percent = 0;
                    if (weekElem) {
                        const texts = Array.from(weekElem.querySelectorAll('p')).map(p => p.textContent.trim());
                        texts.forEach(t => {
                            if (t.includes('%')) weekly_usage = t;
                            if (t.toLowerCase().includes('réinitialisation') || t.toLowerCase().includes('reinitialisation') || t.toLowerCase().includes('reset')) weekly_reset = t;
                        });
                        const indicator = weekElem.querySelector('.progress-indicator');
                        if (indicator) {
                            const style = indicator.getAttribute('style') || '';
                            const match = style.match(/width:\\s*([0-9.]+)%/i);
                            if (match) weekly_percent = parseFloat(match[1]);
                        }
                        if (!weekly_percent && weekly_usage) {
                            const match = weekly_usage.match(/([0-9.]+)/);
                            if (match) weekly_percent = parseFloat(match[1]);
                        }
                    }

                    return {
                        tier: tier || "PRO",
                        description: description,
                        current_usage: current_usage || `${current_percent} %`,
                        current_percent: current_percent,
                        current_reset_time: current_reset,
                        weekly_usage: weekly_usage || `${weekly_percent} %`,
                        weekly_percent: weekly_percent,
                        weekly_reset_time: weekly_reset
                    };
                }
                """)
                return data
            finally:
                await page.close()

    async def get_account_info(self) -> dict:
        """Retrieves currently connected Google Account email, name, and plan tier."""
        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()
            info = await page.evaluate("""
            () => {
                let email = '';
                let name = '';
                let tier = 'Free (Standard)';

                // 1. Account profile icon / button
                const accBtn = document.querySelector("[aria-label*='Compte Google'], [aria-label*='Google Account'], [aria-label*='@'], a[href*='accounts.google.com'], button[data-test-id='user-profile-button']");
                const aria = accBtn ? (accBtn.getAttribute('aria-label') || '') : '';
                const emailMatch = aria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                if (emailMatch) email = emailMatch[1];

                const nameMatch = aria.match(/(?:Compte Google|Google Account)\\s*:\\s*([^(\\n]+)/i);
                if (nameMatch) name = nameMatch[1].trim();

                // 2. Subscription / Plan Tier detection
                const logoText = document.body.innerText.slice(0, 1500);
                const advBadge = document.querySelector("[aria-label*='Advanced'], [aria-label*='Pro'], .subscription-badge, .tier-pill, mat-chip");
                if (advBadge || /gemini advanced/i.test(logoText) || /advanced/i.test(document.title)) {
                    tier = 'Pro (Advanced)';
                }

                return {
                    email: email || 'Unknown',
                    name: name || (email ? email.split('@')[0] : 'Unknown'),
                    tier: tier,
                    authenticated: !!email,
                };
            }
            """)
            return info

    async def send_prompt(
        self,
        prompt: str,
        new_chat: bool = False,
        timeout_seconds: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        """Sends a prompt to Gemini and awaits the complete response."""
        timeout = timeout_seconds or settings.DEFAULT_TIMEOUT_SECONDS

        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()

            if new_chat:
                await self.new_chat(page)

            if model:
                await self._switch_model_if_needed(page, model)

            # 1. Exact initial count
            initial_state = await page.evaluate(JS_MONITOR_SCRIPT)
            initial_count = initial_state.get("count", 0)

            # 2. Inject and submit prompt
            await self._prepare_input(page, prompt)
            logger.info("Prompt sent (initial_count=%d), monitoring response in real time...", initial_count)
            start_time = time.time()

            last_text = ""
            stable_ticks = 0
            generation_started = False
            poll_interval = 0.12

            while (time.time() - start_time) < timeout:
                state = await page.evaluate(JS_MONITOR_SCRIPT)
                current_count = state.get("count", 0)
                is_generating = state.get("is_generating", False)
                has_actions = state.get("has_actions", False)
                is_send_enabled = state.get("is_send_enabled", False)
                current_text = state.get("text", "")

                if is_generating or current_count > initial_count:
                    generation_started = True

                if generation_started and current_count > initial_count and current_text:
                    if current_text == last_text and not is_generating:
                        stable_ticks += 1
                        required_ticks = 2 if has_actions else (4 if is_send_enabled else 8)
                        if stable_ticks >= required_ticks:
                            logger.info("Generation completed successfully.")
                            return current_text
                    else:
                        stable_ticks = 0
                        last_text = current_text

                await asyncio.sleep(poll_interval)

            if last_text:
                return last_text

            raise TimeoutError(f"Timeout reached ({timeout}s) without response from Gemini.")

    async def stream_prompt(
        self,
        prompt: str,
        new_chat: bool = False,
        timeout_seconds: Optional[int] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Sends a prompt and streams the response text in real time."""
        timeout = timeout_seconds or settings.DEFAULT_TIMEOUT_SECONDS

        async with self.manager.lock:
            page = await self.manager.get_or_create_gemini_page()
            await page.bring_to_front()

            if new_chat:
                await self.new_chat(page)

            if model:
                await self._switch_model_if_needed(page, model)

            initial_state = await page.evaluate(JS_MONITOR_SCRIPT)
            initial_count = initial_state.get("count", 0)

            await self._prepare_input(page, prompt)
            start_time = time.time()
            last_text = ""
            stable_ticks = 0
            generation_started = False
            poll_interval = 0.08

            while (time.time() - start_time) < timeout:
                state = await page.evaluate(JS_MONITOR_SCRIPT)
                current_count = state.get("count", 0)
                is_generating = state.get("is_generating", False)
                has_actions = state.get("has_actions", False)
                is_send_enabled = state.get("is_send_enabled", False)
                current_text = state.get("text", "")

                if is_generating or current_count > initial_count:
                    generation_started = True

                if generation_started and current_count > initial_count and current_text:
                    if current_text.startswith(last_text) and len(current_text) > len(last_text):
                        chunk = current_text[len(last_text):]
                        last_text = current_text
                        stable_ticks = 0
                        yield (chunk, current_text)
                    elif len(current_text) != len(last_text):
                        # Text updated or reformatted (e.g. Markdown code block enclosed)
                        common_len = 0
                        min_l = min(len(last_text), len(current_text))
                        for i in range(min_l):
                            if last_text[i] == current_text[i]:
                                common_len += 1
                            else:
                                break
                        chunk = current_text[common_len:]
                        last_text = current_text
                        stable_ticks = 0
                        if chunk:
                            yield (chunk, current_text)
                        else:
                            yield ("", current_text)
                    elif current_text == last_text and not is_generating:
                        stable_ticks += 1
                        required_ticks = 2 if has_actions else (4 if is_send_enabled else 8)
                        if stable_ticks >= required_ticks:
                            break

                await asyncio.sleep(poll_interval)

            if last_text:
                yield ("", last_text)


gemini_driver = GeminiDriver(cdp_manager)

