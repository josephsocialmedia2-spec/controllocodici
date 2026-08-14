using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.IO;
using System.Net;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace MemoryDirector
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            if (args != null && args.Length > 0 && string.Equals(args[0], "--self-test", StringComparison.OrdinalIgnoreCase))
            {
                Environment.Exit(SelfTests.Run());
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    internal sealed class MemoryPlan
    {
        public string title { get; set; }
        public string simple_meaning { get; set; }
        public List<string> micro_concepts { get; set; }
        public List<string> guided_movie { get; set; }
        public string final_freeze_frame { get; set; }
        public List<string> recall_questions { get; set; }
    }

    internal sealed class GenerateRequest
    {
        public string model { get; set; }
        public string prompt { get; set; }
        public bool stream { get; set; }
        public string format { get; set; }
        public Dictionary<string, object> options { get; set; }
    }

    internal sealed class GenerateResponse
    {
        public string response { get; set; }
        public string error { get; set; }
    }

    internal sealed class TagsResponse
    {
        public List<ModelInfo> models { get; set; }
    }

    internal sealed class ModelInfo
    {
        public string name { get; set; }
        public string model { get; set; }
    }

    internal sealed class OllamaClient
    {
        private readonly JavaScriptSerializer serializer = new JavaScriptSerializer();
        private readonly string baseUrl;
        private readonly string model;

        public OllamaClient(string baseUrl, string model)
        {
            this.baseUrl = baseUrl.TrimEnd('/');
            this.model = model;
            ServicePointManager.Expect100Continue = false;
        }

        public string ModelName
        {
            get { return model; }
        }

        public bool HealthCheck(out string details)
        {
            try
            {
                string json = HttpGet(baseUrl + "/api/tags", 8000);
                TagsResponse tags = serializer.Deserialize<TagsResponse>(json);
                if (tags == null || tags.models == null)
                {
                    details = "Ollama risponde, ma /api/tags non contiene la lista modelli.";
                    return false;
                }

                bool found = false;
                foreach (ModelInfo info in tags.models)
                {
                    string candidate = info == null ? null : (string.IsNullOrEmpty(info.name) ? info.model : info.name);
                    if (!string.IsNullOrEmpty(candidate) && candidate.StartsWith(model, StringComparison.OrdinalIgnoreCase))
                    {
                        found = true;
                        break;
                    }
                }

                details = found
                    ? "Ollama OK. Modello " + model + " disponibile."
                    : "Ollama OK, ma il modello " + model + " non compare in /api/tags.";
                return found;
            }
            catch (Exception ex)
            {
                details = ex.Message;
                return false;
            }
        }

        public string MiniGenerateTest()
        {
            GenerateRequest request = new GenerateRequest();
            request.model = model;
            request.prompt = "Rispondi soltanto con la parola OK.";
            request.stream = false;
            request.options = new Dictionary<string, object>();
            request.options["temperature"] = 0.0;

            string json = serializer.Serialize(request);
            string raw = HttpPost(baseUrl + "/api/generate", json, 120000);
            GenerateResponse response = serializer.Deserialize<GenerateResponse>(raw);
            if (response == null)
            {
                throw new InvalidOperationException("Risposta Ollama vuota.");
            }
            if (!string.IsNullOrEmpty(response.error))
            {
                throw new InvalidOperationException("Ollama: " + response.error);
            }
            if (string.IsNullOrWhiteSpace(response.response))
            {
                throw new InvalidOperationException("Ollama ha risposto senza testo.");
            }
            return response.response.Trim();
        }

        public MemoryPlan GeneratePlan(string sourceText, int intensity, string objects, string emotions)
        {
            if (string.IsNullOrWhiteSpace(sourceText))
            {
                throw new ArgumentException("Il testo da memorizzare e vuoto.");
            }

            GenerateRequest request = new GenerateRequest();
            request.model = model;
            request.prompt = MnemonicPromptBuilder.Build(sourceText, intensity, objects, emotions);
            request.stream = false;
            request.format = "json";
            request.options = new Dictionary<string, object>();
            request.options["temperature"] = 0.75;

            string body = serializer.Serialize(request);
            string raw = HttpPost(baseUrl + "/api/generate", body, 360000);
            GenerateResponse response = serializer.Deserialize<GenerateResponse>(raw);

            if (response == null)
            {
                throw new InvalidOperationException("Ollama non ha restituito una risposta valida.");
            }
            if (!string.IsNullOrEmpty(response.error))
            {
                throw new InvalidOperationException("Ollama: " + response.error);
            }
            if (string.IsNullOrWhiteSpace(response.response))
            {
                throw new InvalidOperationException("Il modello non ha restituito il contenuto della seduta.");
            }

            string innerJson = NormalizeJson(response.response);
            MemoryPlan plan;
            try
            {
                plan = serializer.Deserialize<MemoryPlan>(innerJson);
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException("Il modello ha restituito JSON non valido. Risposta grezza:\r\n" + response.response, ex);
            }

            ValidatePlan(plan);
            return plan;
        }

        internal static string NormalizeJson(string text)
        {
            string value = (text ?? string.Empty).Trim();
            if (value.StartsWith("```json", StringComparison.OrdinalIgnoreCase))
            {
                value = value.Substring(7).TrimStart();
            }
            else if (value.StartsWith("```", StringComparison.Ordinal))
            {
                value = value.Substring(3).TrimStart();
            }

            if (value.EndsWith("```", StringComparison.Ordinal))
            {
                value = value.Substring(0, value.Length - 3).TrimEnd();
            }
            return value;
        }

        internal static void ValidatePlan(MemoryPlan plan)
        {
            if (plan == null)
            {
                throw new InvalidOperationException("Seduta nulla.");
            }
            if (string.IsNullOrWhiteSpace(plan.title))
            {
                throw new InvalidOperationException("La seduta non contiene un titolo.");
            }
            if (string.IsNullOrWhiteSpace(plan.simple_meaning))
            {
                throw new InvalidOperationException("La seduta non contiene il significato semplice.");
            }
            if (plan.micro_concepts == null || plan.micro_concepts.Count == 0)
            {
                throw new InvalidOperationException("La seduta non contiene micro-concetti.");
            }
            if (plan.guided_movie == null || plan.guided_movie.Count == 0)
            {
                throw new InvalidOperationException("La seduta non contiene il film mentale.");
            }
            if (plan.guided_movie[0].IndexOf("Chiudi gli occhi", StringComparison.OrdinalIgnoreCase) < 0)
            {
                plan.guided_movie.Insert(0, "Chiudi gli occhi. Immagina...");
            }
            if (string.IsNullOrWhiteSpace(plan.final_freeze_frame))
            {
                throw new InvalidOperationException("La seduta non contiene il fotogramma finale.");
            }
            if (plan.recall_questions == null)
            {
                plan.recall_questions = new List<string>();
            }
        }

        private static string HttpGet(string url, int timeoutMs)
        {
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
            request.Method = "GET";
            request.Timeout = timeoutMs;
            request.ReadWriteTimeout = timeoutMs;
            request.Proxy = null;

            try
            {
                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                using (Stream stream = response.GetResponseStream())
                using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                {
                    return reader.ReadToEnd();
                }
            }
            catch (WebException ex)
            {
                throw BuildWebException(ex, url);
            }
        }

        private static string HttpPost(string url, string json, int timeoutMs)
        {
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
            request.Method = "POST";
            request.ContentType = "application/json; charset=utf-8";
            request.Accept = "application/json";
            request.Timeout = timeoutMs;
            request.ReadWriteTimeout = timeoutMs;
            request.ContentLength = bytes.Length;
            request.Proxy = null;

            try
            {
                using (Stream requestStream = request.GetRequestStream())
                {
                    requestStream.Write(bytes, 0, bytes.Length);
                }

                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                using (Stream stream = response.GetResponseStream())
                using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                {
                    return reader.ReadToEnd();
                }
            }
            catch (WebException ex)
            {
                throw BuildWebException(ex, url);
            }
        }

        private static Exception BuildWebException(WebException ex, string url)
        {
            string detail = ex.Message;
            HttpWebResponse response = ex.Response as HttpWebResponse;
            if (response != null)
            {
                try
                {
                    using (Stream stream = response.GetResponseStream())
                    using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                    {
                        string body = reader.ReadToEnd();
                        if (!string.IsNullOrWhiteSpace(body))
                        {
                            detail += "\r\nHTTP " + (int)response.StatusCode + " " + response.StatusDescription + "\r\n" + body;
                        }
                    }
                }
                catch
                {
                }
            }
            return new InvalidOperationException("Errore collegamento a " + url + ":\r\n" + detail, ex);
        }
    }

    internal static class MnemonicPromptBuilder
    {
        public static string Build(string sourceText, int intensity, string objects, string emotions)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("Sei MEMORY DIRECTOR, un regista di memorizzazione guidata in italiano.");
            sb.AppendLine();
            sb.AppendLine("TESTO DA ASSIMILARE:");
            sb.AppendLine(sourceText);
            sb.AppendLine();
            sb.AppendLine("PROFILO:");
            sb.AppendLine("- intensita PAV: " + intensity + "/10");
            sb.AppendLine("- oggetti o immagini familiari: " + (objects ?? string.Empty));
            sb.AppendLine("- trigger emotivi: " + (emotions ?? string.Empty));
            sb.AppendLine();
            sb.AppendLine("OBIETTIVO:");
            sb.AppendLine("Trasforma il significato in un piccolo FILM MENTALE costruito progressivamente nella mente dell'utente mentre ascolta una voce guida.");
            sb.AppendLine();
            sb.AppendLine("REGOLE OBBLIGATORIE:");
            sb.AppendLine("1. Comprendi il concetto prima di memorizzarlo.");
            sb.AppendLine("2. Spacchettalo in massimo 6 micro-concetti che permettono di ricostruire il significato finale.");
            sb.AppendLine("3. Non fare una lezione e non creare una scheda statica.");
            sb.AppendLine("4. La prima battuta deve essere esattamente: Chiudi gli occhi. Immagina...");
            sb.AppendLine("5. Costruisci la scena un elemento alla volta.");
            sb.AppendLine("6. Usa PAV: Paradosso, Azione, Vivido.");
            sb.AppendLine("7. Inserisci movimento, sproporzione, sorpresa e micro-suoni come CLACK, BOOM, CRACK o SCHHH quando aiutano.");
            sb.AppendLine("8. Usa tatto, temperatura, odore e gusto solo quando sono naturali per la scena.");
            sb.AppendLine("9. La scena deve suscitare una reazione emotiva utile: desiderio, sorpresa, comicita, tensione, soddisfazione o altro.");
            sb.AppendLine("10. Non inventare falsi ricordi biografici. Puoi invitare l'utente a richiamare una propria esperienza simile.");
            sb.AppendLine("11. Trasforma le astrazioni in persone, oggetti e azioni concrete.");
            sb.AppendLine("12. Inserisci [pausa] come elemento autonomo quando la voce deve lasciare tempo alla visualizzazione.");
            sb.AppendLine("13. Termina con un FOTOGRAMMA FINALE netto che riassuma chi ha cosa, cosa e cambiato e qual e il concetto.");
            sb.AppendLine("14. Crea poi 4 domande di ACTIVE RECALL senza fornire subito le risposte.");
            sb.AppendLine("15. Frasi brevi, ritmiche, facili da ascoltare a occhi chiusi.");
            sb.AppendLine("16. Non promettere memoria perfetta.");
            sb.AppendLine();
            sb.AppendLine("Restituisci SOLO JSON valido con questa struttura:");
            sb.AppendLine("{");
            sb.AppendLine("  \"title\": \"...\",");
            sb.AppendLine("  \"simple_meaning\": \"...\",");
            sb.AppendLine("  \"micro_concepts\": [\"...\"],");
            sb.AppendLine("  \"guided_movie\": [\"Chiudi gli occhi. Immagina...\", \"[pausa]\", \"...\"],");
            sb.AppendLine("  \"final_freeze_frame\": \"...\",");
            sb.AppendLine("  \"recall_questions\": [\"...\"]");
            sb.AppendLine("}");
            return sb.ToString();
        }
    }

    internal sealed class MainForm : Form
    {
        private readonly OllamaClient client = new OllamaClient("http://127.0.0.1:11434", "qwen3:4b");
        private readonly TextBox sourceBox = new TextBox();
        private readonly RichTextBox outputBox = new RichTextBox();
        private readonly Button generateButton = new Button();
        private readonly Button exampleButton = new Button();
        private readonly Button testButton = new Button();
        private readonly Button speakButton = new Button();
        private readonly Button stopButton = new Button();
        private readonly Button recallButton = new Button();
        private readonly Button showPlanButton = new Button();
        private readonly Label statusLabel = new Label();
        private readonly TrackBar intensityTrack = new TrackBar();
        private readonly Label intensityLabel = new Label();
        private readonly TextBox objectsBox = new TextBox();
        private readonly TextBox emotionsBox = new TextBox();
        private readonly BackgroundWorker generateWorker = new BackgroundWorker();
        private readonly BackgroundWorker testWorker = new BackgroundWorker();
        private object speaker;
        private MemoryPlan currentPlan;

        public MainForm()
        {
            Text = "Memory Director - Stable";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(1050, 690);
            Size = new Size(1220, 780);
            BackColor = Color.FromArgb(244, 246, 248);
            Font = new Font("Segoe UI", 10F);

            BuildUi();
            WireEvents();
        }

        private void BuildUi()
        {
            Label title = new Label();
            title.Text = "MEMORY DIRECTOR";
            title.Font = new Font("Segoe UI", 19F, FontStyle.Bold);
            title.AutoSize = true;
            title.Location = new Point(20, 15);
            Controls.Add(title);

            Label version = new Label();
            version.Text = "C# WINDOWS BUILD - diretto a Ollama localhost:11434";
            version.ForeColor = Color.RoyalBlue;
            version.AutoSize = true;
            version.Location = new Point(23, 52);
            Controls.Add(version);

            SplitContainer split = new SplitContainer();
            split.Location = new Point(20, 82);
            split.Size = new Size(ClientSize.Width - 40, ClientSize.Height - 105);
            split.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            split.SplitterDistance = 555;
            split.Panel1.Padding = new Padding(10);
            split.Panel2.Padding = new Padding(10);
            Controls.Add(split);

            Label leftTitle = new Label();
            leftTitle.Text = "1. Materiale da memorizzare";
            leftTitle.Font = new Font("Segoe UI", 12F, FontStyle.Bold);
            leftTitle.AutoSize = true;
            leftTitle.Location = new Point(5, 5);
            split.Panel1.Controls.Add(leftTitle);

            sourceBox.Multiline = true;
            sourceBox.ScrollBars = ScrollBars.Vertical;
            sourceBox.Location = new Point(5, 38);
            sourceBox.Size = new Size(split.Panel1.ClientSize.Width - 10, 285);
            sourceBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            sourceBox.Font = new Font("Segoe UI", 11F);
            split.Panel1.Controls.Add(sourceBox);

            generateButton.Text = "GENERA SEDUTA";
            generateButton.Location = new Point(5, 335);
            generateButton.Size = new Size(145, 40);
            generateButton.BackColor = Color.FromArgb(17, 24, 39);
            generateButton.ForeColor = Color.White;
            generateButton.FlatStyle = FlatStyle.Flat;
            split.Panel1.Controls.Add(generateButton);

            exampleButton.Text = "ESEMPIO: LA VENDITA";
            exampleButton.Location = new Point(158, 335);
            exampleButton.Size = new Size(175, 40);
            split.Panel1.Controls.Add(exampleButton);

            testButton.Text = "TEST MOTORE AI";
            testButton.Location = new Point(341, 335);
            testButton.Size = new Size(155, 40);
            split.Panel1.Controls.Add(testButton);

            statusLabel.Text = "Pronto.";
            statusLabel.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
            statusLabel.Location = new Point(5, 388);
            statusLabel.Size = new Size(split.Panel1.ClientSize.Width - 10, 42);
            statusLabel.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            split.Panel1.Controls.Add(statusLabel);

            intensityLabel.Text = "Intensita PAV: 9/10";
            intensityLabel.Location = new Point(5, 438);
            intensityLabel.AutoSize = true;
            split.Panel1.Controls.Add(intensityLabel);

            intensityTrack.Minimum = 1;
            intensityTrack.Maximum = 10;
            intensityTrack.Value = 9;
            intensityTrack.TickStyle = TickStyle.None;
            intensityTrack.Location = new Point(5, 460);
            intensityTrack.Size = new Size(split.Panel1.ClientSize.Width - 10, 36);
            intensityTrack.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            split.Panel1.Controls.Add(intensityTrack);

            Label objectsLabel = new Label();
            objectsLabel.Text = "Oggetti/immagini che ti vengono naturali";
            objectsLabel.AutoSize = true;
            objectsLabel.Location = new Point(5, 510);
            split.Panel1.Controls.Add(objectsLabel);

            objectsBox.Text = "bicicletta, casa, denaro, automobile, oggetti enormi";
            objectsBox.Location = new Point(5, 533);
            objectsBox.Size = new Size(split.Panel1.ClientSize.Width - 10, 27);
            objectsBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            split.Panel1.Controls.Add(objectsBox);

            Label emotionsLabel = new Label();
            emotionsLabel.Text = "Trigger emotivi utili";
            emotionsLabel.AutoSize = true;
            emotionsLabel.Location = new Point(5, 570);
            split.Panel1.Controls.Add(emotionsLabel);

            emotionsBox.Text = "desiderio, sorpresa, comicita, competizione, soddisfazione";
            emotionsBox.Location = new Point(5, 593);
            emotionsBox.Size = new Size(split.Panel1.ClientSize.Width - 10, 27);
            emotionsBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            split.Panel1.Controls.Add(emotionsBox);

            Label rightTitle = new Label();
            rightTitle.Text = "2. Seduta";
            rightTitle.Font = new Font("Segoe UI", 12F, FontStyle.Bold);
            rightTitle.AutoSize = true;
            rightTitle.Location = new Point(5, 5);
            split.Panel2.Controls.Add(rightTitle);

            speakButton.Text = "AVVIA VOCE GUIDATA";
            speakButton.Location = new Point(5, 38);
            speakButton.Size = new Size(175, 40);
            speakButton.BackColor = Color.FromArgb(17, 24, 39);
            speakButton.ForeColor = Color.White;
            speakButton.FlatStyle = FlatStyle.Flat;
            split.Panel2.Controls.Add(speakButton);

            stopButton.Text = "STOP";
            stopButton.Location = new Point(188, 38);
            stopButton.Size = new Size(75, 40);
            split.Panel2.Controls.Add(stopButton);

            recallButton.Text = "TESTAMI";
            recallButton.Location = new Point(271, 38);
            recallButton.Size = new Size(90, 40);
            split.Panel2.Controls.Add(recallButton);

            showPlanButton.Text = "RIVEDI SEDUTA";
            showPlanButton.Location = new Point(369, 38);
            showPlanButton.Size = new Size(125, 40);
            split.Panel2.Controls.Add(showPlanButton);

            outputBox.ReadOnly = true;
            outputBox.BackColor = Color.White;
            outputBox.Location = new Point(5, 92);
            outputBox.Size = new Size(split.Panel2.ClientSize.Width - 10, split.Panel2.ClientSize.Height - 102);
            outputBox.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            outputBox.Font = new Font("Segoe UI", 11F);
            outputBox.Text = "Genera una seduta per iniziare.";
            split.Panel2.Controls.Add(outputBox);
        }

        private void WireEvents()
        {
            intensityTrack.ValueChanged += delegate
            {
                intensityLabel.Text = "Intensita PAV: " + intensityTrack.Value + "/10";
            };

            exampleButton.Click += delegate
            {
                sourceBox.Text = "La vendita e il contratto che ha per oggetto il trasferimento della proprieta di una cosa o il trasferimento di un altro diritto contro il corrispettivo di un prezzo. La proprieta del bene venduto passa normalmente dal venditore al compratore al momento del consenso fra le parti.";
            };

            generateWorker.DoWork += delegate(object sender, DoWorkEventArgs e)
            {
                GenerationArgs a = (GenerationArgs)e.Argument;
                e.Result = client.GeneratePlan(a.SourceText, a.Intensity, a.Objects, a.Emotions);
            };

            generateWorker.RunWorkerCompleted += delegate(object sender, RunWorkerCompletedEventArgs e)
            {
                generateButton.Enabled = true;
                testButton.Enabled = true;
                generateButton.Text = "GENERA SEDUTA";
                Cursor = Cursors.Default;

                if (e.Error != null)
                {
                    ShowError("ERRORE GENERAZIONE", e.Error);
                    return;
                }

                currentPlan = (MemoryPlan)e.Result;
                outputBox.Text = FormatPlan(currentPlan, true);
                statusLabel.Text = "Seduta pronta.";
            };

            generateButton.Click += delegate
            {
                string text = sourceBox.Text == null ? string.Empty : sourceBox.Text.Trim();
                if (text.Length == 0)
                {
                    statusLabel.Text = "Inserisci prima un testo.";
                    sourceBox.Focus();
                    return;
                }
                if (generateWorker.IsBusy)
                {
                    return;
                }

                GenerationArgs a = new GenerationArgs();
                a.SourceText = text;
                a.Intensity = intensityTrack.Value;
                a.Objects = objectsBox.Text;
                a.Emotions = emotionsBox.Text;

                generateButton.Enabled = false;
                testButton.Enabled = false;
                generateButton.Text = "ELABORAZIONE...";
                Cursor = Cursors.WaitCursor;
                statusLabel.Text = "Testo acquisito: " + text.Length + " caratteri. " + client.ModelName + " sta elaborando...";
                outputBox.Text = "Elaborazione in corso sul PC. Non chiudere Memory Director.";
                generateWorker.RunWorkerAsync(a);
            };

            testWorker.DoWork += delegate(object sender, DoWorkEventArgs e)
            {
                string details;
                if (!client.HealthCheck(out details))
                {
                    throw new InvalidOperationException(details);
                }
                string mini = client.MiniGenerateTest();
                e.Result = details + "\r\nMini-generazione: " + mini;
            };

            testWorker.RunWorkerCompleted += delegate(object sender, RunWorkerCompletedEventArgs e)
            {
                testButton.Enabled = true;
                generateButton.Enabled = true;
                Cursor = Cursors.Default;
                if (e.Error != null)
                {
                    ShowError("TEST MOTORE AI FALLITO", e.Error);
                    return;
                }
                string message = Convert.ToString(e.Result);
                statusLabel.Text = "TEST AI RIUSCITO.";
                MessageBox.Show(this, message, "Memory Director - Test AI", MessageBoxButtons.OK, MessageBoxIcon.Information);
            };

            testButton.Click += delegate
            {
                if (testWorker.IsBusy)
                {
                    return;
                }
                testButton.Enabled = false;
                generateButton.Enabled = false;
                Cursor = Cursors.WaitCursor;
                statusLabel.Text = "Test completo Ollama e qwen3:4b...";
                testWorker.RunWorkerAsync();
            };

            speakButton.Click += delegate
            {
                if (currentPlan == null || currentPlan.guided_movie == null)
                {
                    statusLabel.Text = "Prima genera una seduta.";
                    return;
                }
                try
                {
                    EnsureSpeaker();
                    StopSpeaker();
                    StringBuilder spoken = new StringBuilder();
                    foreach (string line in currentPlan.guided_movie)
                    {
                        if (string.Equals(line, "[pausa]", StringComparison.OrdinalIgnoreCase))
                        {
                            spoken.Append(" ... ... ");
                        }
                        else if (!string.IsNullOrWhiteSpace(line))
                        {
                            spoken.Append(line);
                            spoken.Append(" ... ");
                        }
                    }
                    speaker.GetType().InvokeMember(
                        "Speak",
                        BindingFlags.InvokeMethod,
                        null,
                        speaker,
                        new object[] { spoken.ToString(), 1 }
                    );
                    statusLabel.Text = "Voce guidata avviata.";
                }
                catch (Exception ex)
                {
                    ShowError("ERRORE VOCE", ex);
                }
            };

            stopButton.Click += delegate
            {
                try
                {
                    StopSpeaker();
                    statusLabel.Text = "Voce fermata.";
                }
                catch
                {
                }
            };

            recallButton.Click += delegate
            {
                if (currentPlan == null)
                {
                    statusLabel.Text = "Prima genera una seduta.";
                    return;
                }
                outputBox.Text = FormatPlan(currentPlan, false);
                statusLabel.Text = "Active Recall: rispondi senza rileggere il film.";
            };

            showPlanButton.Click += delegate
            {
                if (currentPlan != null)
                {
                    outputBox.Text = FormatPlan(currentPlan, true);
                    statusLabel.Text = "Seduta completa.";
                }
            };

            FormClosed += delegate
            {
                if (speaker != null)
                {
                    try { StopSpeaker(); } catch { }
                    try { System.Runtime.InteropServices.Marshal.FinalReleaseComObject(speaker); } catch { }
                    speaker = null;
                }
            };
        }

        private void EnsureSpeaker()
        {
            if (speaker != null)
            {
                return;
            }

            Type sapiType = Type.GetTypeFromProgID("SAPI.SpVoice");
            if (sapiType == null)
            {
                throw new InvalidOperationException("Sintesi vocale Windows SAPI non disponibile.");
            }
            speaker = Activator.CreateInstance(sapiType);
        }

        private void StopSpeaker()
        {
            if (speaker == null)
            {
                return;
            }
            speaker.GetType().InvokeMember(
                "Speak",
                BindingFlags.InvokeMethod,
                null,
                speaker,
                new object[] { string.Empty, 3 }
            );
        }

        private void ShowError(string heading, Exception ex)
        {
            string message = FlattenException(ex);
            statusLabel.Text = heading + ".";
            outputBox.Text = heading + "\r\n\r\n" + message;
            SaveErrorLog(heading, message);
            MessageBox.Show(this, message, heading, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }

        private static string FlattenException(Exception ex)
        {
            StringBuilder sb = new StringBuilder();
            Exception current = ex;
            int depth = 0;
            while (current != null && depth < 6)
            {
                if (depth > 0)
                {
                    sb.AppendLine();
                    sb.AppendLine("Dettaglio:");
                }
                sb.AppendLine(current.Message);
                current = current.InnerException;
                depth++;
            }
            return sb.ToString().Trim();
        }

        private void SaveErrorLog(string heading, string message)
        {
            try
            {
                string path = Path.Combine(Path.GetTempPath(), "MemoryDirector_error.txt");
                File.WriteAllText(path, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "\r\n" + heading + "\r\n\r\n" + message, Encoding.UTF8);
                outputBox.AppendText("\r\n\r\nLog: " + path);
            }
            catch
            {
            }
        }

        private static string FormatPlan(MemoryPlan plan, bool full)
        {
            StringBuilder sb = new StringBuilder();
            if (full)
            {
                sb.AppendLine(plan.title == null ? string.Empty : plan.title.ToUpperInvariant());
                sb.AppendLine();
                sb.AppendLine("SIGNIFICATO SEMPLICE");
                sb.AppendLine(plan.simple_meaning);
                sb.AppendLine();
                sb.AppendLine("MICRO-CONCETTI");
                for (int i = 0; i < plan.micro_concepts.Count; i++)
                {
                    sb.AppendLine((i + 1) + ". " + plan.micro_concepts[i]);
                }
                sb.AppendLine();
                sb.AppendLine("FILM MENTALE");
                foreach (string line in plan.guided_movie)
                {
                    sb.AppendLine(string.Equals(line, "[pausa]", StringComparison.OrdinalIgnoreCase) ? "... pausa ..." : line);
                }
                sb.AppendLine();
                sb.AppendLine("FOTOGRAMMA FINALE");
                sb.AppendLine(plan.final_freeze_frame);
                sb.AppendLine();
            }

            sb.AppendLine("ACTIVE RECALL");
            if (plan.recall_questions == null || plan.recall_questions.Count == 0)
            {
                sb.AppendLine("Nessuna domanda generata.");
            }
            else
            {
                for (int i = 0; i < plan.recall_questions.Count; i++)
                {
                    sb.AppendLine((i + 1) + ". " + plan.recall_questions[i]);
                    sb.AppendLine();
                }
            }
            return sb.ToString();
        }

        private sealed class GenerationArgs
        {
            public string SourceText;
            public int Intensity;
            public string Objects;
            public string Emotions;
        }
    }

    internal static class SelfTests
    {
        public static int Run()
        {
            try
            {
                int passed = 0;
                TestNormalizeJson(); passed++;
                TestPrompt(); passed++;
                TestPlanValidation(); passed++;
                TestNestedOllamaJson(); passed++;
                Console.WriteLine("SELF-TEST OK - " + passed + " test superati.");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("SELF-TEST FAILED");
                Console.Error.WriteLine(ex.ToString());
                return 1;
            }
        }

        private static void TestNormalizeJson()
        {
            string sample = "```json\n{\"title\":\"Vendita\"}\n```";
            string normalized = OllamaClient.NormalizeJson(sample);
            Assert(normalized == "{\"title\":\"Vendita\"}", "NormalizeJson non rimuove correttamente i code fence.");
        }

        private static void TestPrompt()
        {
            string prompt = MnemonicPromptBuilder.Build("La vendita trasferisce un bene contro un prezzo.", 9, "bicicletta", "sorpresa");
            Assert(prompt.IndexOf("Chiudi gli occhi. Immagina", StringComparison.OrdinalIgnoreCase) >= 0, "Prompt privo dell'apertura guidata.");
            Assert(prompt.IndexOf("PAV", StringComparison.OrdinalIgnoreCase) >= 0, "Prompt privo del metodo PAV.");
            Assert(prompt.IndexOf("La vendita", StringComparison.OrdinalIgnoreCase) >= 0, "Prompt privo del testo sorgente.");
        }

        private static void TestPlanValidation()
        {
            MemoryPlan plan = new MemoryPlan();
            plan.title = "Vendita";
            plan.simple_meaning = "Una cosa cambia proprietario in cambio di un prezzo.";
            plan.micro_concepts = new List<string>();
            plan.micro_concepts.Add("venditore");
            plan.guided_movie = new List<string>();
            plan.guided_movie.Add("Vedi una bicicletta enorme.");
            plan.final_freeze_frame = "Uno ha i soldi, l'altro la bicicletta.";
            plan.recall_questions = new List<string>();
            OllamaClient.ValidatePlan(plan);
            Assert(plan.guided_movie.Count == 2, "ValidatePlan non inserisce l'apertura guidata.");
            Assert(plan.guided_movie[0].IndexOf("Chiudi gli occhi", StringComparison.OrdinalIgnoreCase) >= 0, "Apertura guidata errata.");
        }

        private static void TestNestedOllamaJson()
        {
            JavaScriptSerializer serializer = new JavaScriptSerializer();
            MemoryPlan plan = new MemoryPlan();
            plan.title = "Vendita";
            plan.simple_meaning = "Scambio di bene contro prezzo.";
            plan.micro_concepts = new List<string>(new string[] { "bene", "prezzo" });
            plan.guided_movie = new List<string>(new string[] { "Chiudi gli occhi. Immagina...", "Una bici enorme." });
            plan.final_freeze_frame = "Bici da una parte, soldi dall'altra.";
            plan.recall_questions = new List<string>(new string[] { "Chi ha la bici?" });

            GenerateResponse outer = new GenerateResponse();
            outer.response = serializer.Serialize(plan);
            string outerJson = serializer.Serialize(outer);
            GenerateResponse parsedOuter = serializer.Deserialize<GenerateResponse>(outerJson);
            MemoryPlan parsedPlan = serializer.Deserialize<MemoryPlan>(parsedOuter.response);
            Assert(parsedPlan != null && parsedPlan.title == "Vendita", "Parsing della risposta Ollama annidata fallito.");
        }

        private static void Assert(bool condition, string message)
        {
            if (!condition)
            {
                throw new InvalidOperationException(message);
            }
        }
    }
}
