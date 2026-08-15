$ErrorActionPreference = "Stop"

$sourcePath = Join-Path $PSScriptRoot "MemoryDirector.Cascade.cs"
$content = Get-Content -Raw -Encoding UTF8 $sourcePath

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
'@

$content = $content.Substring(0, $testAt) + $testBlock + $content.Substring($testAt)
Set-Content -Path $sourcePath -Value $content -Encoding UTF8
Write-Host "JSON compatibility patch applied."
