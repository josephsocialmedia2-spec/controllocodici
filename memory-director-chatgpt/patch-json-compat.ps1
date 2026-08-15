$ErrorActionPreference = "Stop"

$sourcePath = Join-Path $PSScriptRoot "MemoryDirector.Cascade.cs"
$content = Get-Content -Raw -Encoding UTF8 $sourcePath

# -----------------------------------------------------------------------------
# 1. JSON compatibility: guided_movie may be either an array or one text string.
# -----------------------------------------------------------------------------
$startMarker = "        public static MemoryPlan ParsePlan(string raw)"
$endMarker = "        internal static string NormalizeJson(string raw)"
$start = $content.IndexOf($startMarker)
if ($start -lt 0) { throw "ParsePlan start marker not found" }
$end = $content.IndexOf($endMarker, $start)
if ($end -lt 0) { throw "ParsePlan end marker not found" }

$replacement = @'
        public static MemoryPlan ParsePlan(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
                throw new InvalidOperationException("Gli appunti sono vuoti. Copia prima la risposta JSON di ChatGPT.");

            string json = NormalizeJson(raw);
            JavaScriptSerializer serializer = new JavaScriptSerializer();
            Dictionary<string, object> root;

            try
            {
                object parsed = serializer.DeserializeObject(json);
                root = parsed as Dictionary<string, object>;
                if (root == null)
                    throw new InvalidOperationException("La radice della risposta deve essere un oggetto JSON.");
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException("La risposta non contiene JSON sintatticamente valido: " + ex.Message, ex);
            }

            object guidedValue;
            if (root.TryGetValue("guided_movie", out guidedValue) && guidedValue is string)
            {
                root["guided_movie"] = SplitGuidedMovieText((string)guidedValue);
            }

            MemoryPlan plan;
            try
            {
                string normalizedShape = serializer.Serialize(root);
                plan = serializer.Deserialize<MemoryPlan>(normalizedShape);
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException("Il JSON e valido, ma alcuni campi hanno un formato non compatibile: " + ex.Message, ex);
            }

            NormalizeLegacyPlan(plan);
            ValidatePlan(plan);
            return plan;
        }

        private static List<string> SplitGuidedMovieText(string text)
        {
            List<string> result = new List<string>();
            string value = (text ?? string.Empty).Trim();
            if (value.Length == 0) return result;

            const string pauseMarker = "|||MEMORY_PAUSE|||";
            value = value.Replace("[pausa]", pauseMarker)
                         .Replace("[PAUSA]", pauseMarker)
                         .Replace("[Pausa]", pauseMarker);

            string[] blocks = value.Split(new string[] { pauseMarker }, StringSplitOptions.None);
            for (int b = 0; b < blocks.Length; b++)
            {
                if (b > 0) result.Add("[pausa]");
                string block = (blocks[b] ?? string.Empty).Trim();
                if (block.Length == 0) continue;

                string[] sentences = block.Split(
                    new string[] { ". ", "! ", "? ", "\r\n", "\n" },
                    StringSplitOptions.RemoveEmptyEntries);

                foreach (string sentence in sentences)
                {
                    string line = (sentence ?? string.Empty).Trim();
                    if (line.Length > 0) result.Add(line);
                }
            }

            if (result.Count == 0) result.Add(value);
            return result;
        }

'@

$content = $content.Substring(0, $start) + $replacement + $content.Substring($end)

# -----------------------------------------------------------------------------
# 2. Add Win32 support used to locate and foreground the dedicated ChatGPT tab.
# -----------------------------------------------------------------------------
if ($content.IndexOf("using System.Runtime.InteropServices;") -lt 0)
{
    $usingMarker = "using System.Reflection;"
    $usingAt = $content.IndexOf($usingMarker)
    if ($usingAt -lt 0) { throw "using insertion marker not found" }
    $usingEnd = $usingAt + $usingMarker.Length
    $content = $content.Substring(0, $usingEnd) + "`r`nusing System.Runtime.InteropServices;" + $content.Substring($usingEnd)
}

# -----------------------------------------------------------------------------
# 3. Inject browser-window automation class.
# -----------------------------------------------------------------------------
$classMarker = "    internal sealed class SapiSpeaker"
$classAt = $content.IndexOf($classMarker)
if ($classAt -lt 0) { throw "SapiSpeaker insertion marker not found" }

$automationClass = @'
    internal static class ChatWindowAutomation
    {
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

        public static bool LooksLikeChatWindowTitle(string title)
        {
            if (string.IsNullOrWhiteSpace(title)) return false;
            string value = title.Trim();
            return value.IndexOf("ChatGPT", StringComparison.OrdinalIgnoreCase) >= 0 ||
                   value.IndexOf("OpenAI", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        public static void OpenPasteAndSend(string prompt, Control uiControl)
        {
            if (string.IsNullOrWhiteSpace(prompt))
                throw new ArgumentException("Il prompt da inviare e vuoto.");
            if (uiControl == null)
                throw new ArgumentNullException("uiControl");

            // Clipboard is deliberately kept as a fallback if browser focus is blocked.
            Clipboard.SetText(prompt);
            ChatGptBridge.OpenDedicatedConversation();

            Thread worker = new Thread(delegate()
            {
                IntPtr chatWindow = WaitForChatWindow(15000);
                if (chatWindow == IntPtr.Zero) return;

                Thread.Sleep(1800);
                if (uiControl.IsDisposed || !uiControl.IsHandleCreated) return;

                uiControl.BeginInvoke((MethodInvoker)delegate
                {
                    try
                    {
                        ShowWindowAsync(chatWindow, 9); // SW_RESTORE
                        SetForegroundWindow(chatWindow);
                        Thread.Sleep(350);
                        SendKeys.SendWait("^v");
                        Thread.Sleep(250);
                        SendKeys.SendWait("{ENTER}");
                    }
                    catch
                    {
                        // The complete prompt remains in Clipboard for manual fallback.
                    }
                });
            });

            worker.IsBackground = true;
            worker.Name = "MemoryDirectorChatAutoSend";
            worker.SetApartmentState(ApartmentState.STA);
            worker.Start();
        }

        private static IntPtr WaitForChatWindow(int timeoutMilliseconds)
        {
            int elapsed = 0;
            while (elapsed < timeoutMilliseconds)
            {
                IntPtr found = FindChatWindow();
                if (found != IntPtr.Zero) return found;
                Thread.Sleep(500);
                elapsed += 500;
            }
            return IntPtr.Zero;
        }

        private static IntPtr FindChatWindow()
        {
            IntPtr result = IntPtr.Zero;
            EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
            {
                if (!IsWindowVisible(hWnd)) return true;
                StringBuilder title = new StringBuilder(512);
                GetWindowText(hWnd, title, title.Capacity);
                if (LooksLikeChatWindowTitle(title.ToString()))
                {
                    result = hWnd;
                    return false;
                }
                return true;
            }, IntPtr.Zero);
            return result;
        }
    }

'@

$content = $content.Substring(0, $classAt) + $automationClass + $content.Substring($classAt)

# -----------------------------------------------------------------------------
# 4. Replace PREPARA button behavior: open dedicated chat, paste and press Enter.
# -----------------------------------------------------------------------------
$prepareStartMarker = "            prepareButton.Click += delegate"
$prepareEndMarker = "            importButton.Click += delegate"
$prepareStart = $content.IndexOf($prepareStartMarker)
if ($prepareStart -lt 0) { throw "Prepare handler start marker not found" }
$prepareEnd = $content.IndexOf($prepareEndMarker, $prepareStart)
if ($prepareEnd -lt 0) { throw "Prepare handler end marker not found" }

$newPrepareHandler = @'
            prepareButton.Click += delegate
            {
                if (string.IsNullOrWhiteSpace(sourceBox.Text)) { statusLabel.Text = "Inserisci prima un testo."; return; }
                try
                {
                    string prompt = ChatGptBridge.BuildPrompt(sourceBox.Text, intensityTrack.Value, objectsBox.Text, emotionsBox.Text);
                    ChatWindowAutomation.OpenPasteAndSend(prompt, this);
                    statusLabel.Text = "Apro la chat dedicata e invio automaticamente il prompt...";
                    outputBox.Text = "INVIO AUTOMATICO IN CHATGPT IN CORSO.\r\n\r\nIl programma apre la conversazione dedicata, porta ChatGPT in primo piano, incolla il prompt e preme INVIO.\r\n\r\nIl prompt resta anche negli appunti come sicurezza.";
                }
                catch (Exception ex) { ShowError(ex); }
            };
'@

$content = $content.Substring(0, $prepareStart) + $newPrepareHandler + $content.Substring($prepareEnd)

# -----------------------------------------------------------------------------
# 5. Self-tests for both JSON compatibility and ChatGPT window detection.
# -----------------------------------------------------------------------------
$testMarker = '            failures += Test("Voice rate clamp"'
$testAt = $content.IndexOf($testMarker)
if ($testAt -lt 0) { throw "Self-test insertion marker not found" }

$testBlock = @'
            string stringMovieJson = "{\"title\":\"Vendita\",\"key_question\":\"Quando passa la proprieta?\",\"core_concept\":\"Vendita = diritto contro prezzo.\",\"cascade_branches\":[{\"branch\":\"Effetti\",\"details\":[\"consenso -> effetti reali\"],\"example\":\"\"}],\"mnemonic_anchors\":[{\"concept\":\"Trascrizione\",\"image\":\"registro enorme\"}],\"guided_movie\":\"Immagina una casa enorme. Il venditore stringe la mano al compratore. [pausa] Due compratori corrono verso un registro gigante.\",\"final_freeze_frame\":\"Casa e registro.\",\"recall_questions\":[\"Quando passa?\",\"Qual e la regola?\",\"Quale ramo?\",\"Quale eccezione?\"]}";
            try
            {
                MemoryPlan stringMoviePlan = ChatGptBridge.ParsePlan(stringMovieJson);
                failures += Test("Accept guided_movie as string", stringMoviePlan != null && stringMoviePlan.guided_movie != null && stringMoviePlan.guided_movie.Count >= 3 && stringMoviePlan.guided_movie[0].IndexOf("Chiudi gli occhi", StringComparison.OrdinalIgnoreCase) >= 0);
            }
            catch (Exception ex) { Console.WriteLine("FAIL guided_movie string compatibility: " + ex.Message); failures++; }
            failures += Test("Recognize ChatGPT window title", ChatWindowAutomation.LooksLikeChatWindowTitle("Vendita - ChatGPT") && ChatWindowAutomation.LooksLikeChatWindowTitle("OpenAI - ChatGPT") && !ChatWindowAutomation.LooksLikeChatWindowTitle("Memory Director"));
'@

$content = $content.Substring(0, $testAt) + $testBlock + $content.Substring($testAt)

Set-Content -Path $sourcePath -Value $content -Encoding UTF8
Write-Host "JSON compatibility + ChatGPT auto-send patch applied."
