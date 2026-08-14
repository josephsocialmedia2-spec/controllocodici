using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Reflection;
using System.Text;
using System.Threading;
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
            if (response == null || string.IsNullOrWhiteSpace(response.response))
            {
                throw new InvalidOperationException("Ollama non ha restituito testo.");
            }
            if (!string.IsNullOrEmpty(response.error))
            {
                throw new InvalidOperationException("Ollama: " + response.error);
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

            if (response == null || string.IsNullOrWhiteSpace(response.response))
            {
                throw new InvalidOperationException("Ollama non ha restituito il contenuto della seduta.");
            }
            if (!string.IsNullOrEmpty(response.error))
            {
                throw new InvalidOperationException("Ollama: " + response.error);
            }

            return PlanParser.Parse(response.response);
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

    internal static class PlanParser
    {
        private static readonly JavaScriptSerializer serializer = new JavaScriptSerializer();

        public static MemoryPlan Parse(string text)
        {
            string json = NormalizeJson(text);
            MemoryPlan plan;
            try
            {
                plan = serializer.Deserialize<MemoryPlan>(json);
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException("La risposta non contiene JSON valido.\r\n\r\nRISPOSTA:\r\n" + text, ex);
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
            if (plan == null) throw new InvalidOperationException("Seduta nulla.");
            if (string.IsNullOrWhiteSpace(plan.title)) throw new InvalidOperationException("Manca il titolo.");
            if (string.IsNullOrWhiteSpace(plan.simple_meaning)) throw new InvalidOperationException("Manca il significato semplice.");
            if (plan.micro_concepts == null || plan.micro_concepts.Count == 0) throw new InvalidOperationException("Mancano i micro-concetti.");
            if (plan.guided_movie == null || plan.guided_movie.Count == 0) throw new InvalidOperationException("Manca il film mentale.");
            if (plan.guided_movie[0].IndexOf("Chiudi gli occhi", StringComparison.OrdinalIgnoreCase) < 0)
            {
                plan.guided_movie.Insert(0, "Chiudi gli occhi. Immagina...");
            }
            if (string.IsNullOrWhiteSpace(plan.final_freeze_frame)) throw new InvalidOperationException("Manca il fotogramma finale.");
            if (plan.recall_questions == null) plan.recall_questions = new List<string>();
        }
    }

    internal static class MnemonicPromptBuilder
    {
        public const string DedicatedChatUrl = "https://chatgpt.com/c/6a7a16c8-8a94-83eb-9492-001e95b12c67";

        public static string Build(string sourceText, int intensity, string objects, string emotions)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("Sei MEMORY DIRECTOR, un regista di memorizzazione guidata in italiano.");
            sb.AppendLine("Questa conversazione e dedicata esclusivamente alla trasformazione di concetti in sedute di memoria guidata.");
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
            sb.AppendLine("IMPORTANTE: restituisci SOLO JSON valido, senza testo prima o dopo, con questa struttura:");
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
        private readonly OllamaClient ollama = new OllamaClient("http://127.0.0.1:11434", "qwen3:4b");
        private readonly TextBox sourceBox = new TextBox();
        private readonly RichTextBox outputBox = new RichTextBox();
        private readonly Label statusLabel = new Label();
        private readonly TrackBar intensityTrack = new TrackBar();
        private readonly Label intensityLabel = new Label();
        private readonly TextBox objectsBox = new TextBox();
        private readonly TextBox emotionsBox = new TextBox();
        private readonly BackgroundWorker ollamaWorker = new BackgroundWorker();
        private readonly BackgroundWorker testWorker = new BackgroundWorker();
        private MemoryPlan currentPlan;
        private object sapiVoice;
        private Type sapiVoiceType;

        public MainForm()
        {
            Text = "Memory Director - ChatGPT dedicato";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(1080, 720);
            Size = new Size(1280, 820);
            BackColor = Color.FromArgb(244, 246, 248);
            Font = new Font("Segoe UI", 10F);
            BuildUi();
            WireWorkers();
        }

        private Button MakeButton(string text, int left, int top, int width, EventHandler handler, bool dark)
        {
            Button button = new Button();
            button.Text = text;
            button.Location = new Point(left, top);
            button.Size = new Size(width, 40);
            if (dark)
            {
                button.BackColor = Color.FromArgb(17, 24, 39);
                button.ForeColor = Color.White;
                button.FlatStyle = FlatStyle.Flat;
            }
            button.Click += handler;
            return button;
        }

        private void BuildUi()
        {
            Label title = new Label();
            title.Text = "MEMORY DIRECTOR";
            title.Font = new Font("Segoe UI", 20F, FontStyle.Bold);
            title.AutoSize = true;
            title.Location = new Point(20, 12);
            Controls.Add(title);

            Label version = new Label();
            version.Text = "CHATGPT DEDICATO + OLLAMA FALLBACK";
            version.ForeColor = Color.RoyalBlue;
            version.AutoSize = true;
            version.Location = new Point(23, 52);
            Controls.Add(version);

            SplitContainer split = new SplitContainer();
            split.Location = new Point(20, 82);
            split.Size = new Size(ClientSize.Width - 40, ClientSize.Height - 105);
            split.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            split.SplitterDistance = 600;
            Controls.Add(split);

            GroupBox left = new GroupBox();
            left.Text = "1. Materiale da memorizzare";
            left.Dock = DockStyle.Fill;
            left.Font = new Font("Segoe UI", 11F, FontStyle.Bold);
            split.Panel1.Controls.Add(left);

            sourceBox.Multiline = true;
            sourceBox.ScrollBars = ScrollBars.Vertical;
            sourceBox.AcceptsReturn = true;
            sourceBox.Font = new Font("Segoe UI", 11F);
            sourceBox.Location = new Point(16, 30);
            sourceBox.Size = new Size(left.ClientSize.Width - 32, 285);
            sourceBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            left.Controls.Add(sourceBox);

            Button chatButton = MakeButton("COPIA PROMPT + APRI CHATGPT", 16, 325, 250, ChatButton_Click, true);
            left.Controls.Add(chatButton);
            Button importButton = MakeButton("IMPORTA RISPOSTA CHATGPT", 276, 325, 220, ImportButton_Click, false);
            left.Controls.Add(importButton);
            Button exampleButton = MakeButton("ESEMPIO: LA VENDITA", 16, 375, 210, ExampleButton_Click, false);
            left.Controls.Add(exampleButton);
            Button ollamaButton = MakeButton("GENERA CON OLLAMA", 236, 375, 180, OllamaButton_Click, false);
            left.Controls.Add(ollamaButton);
            Button testButton = MakeButton("TEST OLLAMA", 426, 375, 150, TestButton_Click, false);
            left.Controls.Add(testButton);

            statusLabel.Text = "Pronto. ChatGPT dedicato e il metodo principale.";
            statusLabel.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            statusLabel.Location = new Point(16, 425);
            statusLabel.Size = new Size(left.ClientSize.Width - 32, 44);
            statusLabel.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            left.Controls.Add(statusLabel);

            Label urlLabel = new Label();
            urlLabel.Text = "Conversazione dedicata:";
            urlLabel.AutoSize = true;
            urlLabel.Location = new Point(16, 475);
            left.Controls.Add(urlLabel);

            TextBox urlBox = new TextBox();
            urlBox.ReadOnly = true;
            urlBox.Text = MnemonicPromptBuilder.DedicatedChatUrl;
            urlBox.Location = new Point(16, 498);
            urlBox.Size = new Size(left.ClientSize.Width - 32, 28);
            urlBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            left.Controls.Add(urlBox);

            intensityLabel.Text = "Intensita PAV: 9/10";
            intensityLabel.AutoSize = true;
            intensityLabel.Location = new Point(16, 540);
            left.Controls.Add(intensityLabel);

            intensityTrack.Minimum = 1;
            intensityTrack.Maximum = 10;
            intensityTrack.Value = 9;
            intensityTrack.TickStyle = TickStyle.None;
            intensityTrack.Location = new Point(16, 562);
            intensityTrack.Size = new Size(left.ClientSize.Width - 32, 34);
            intensityTrack.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            intensityTrack.ValueChanged += delegate { intensityLabel.Text = "Intensita PAV: " + intensityTrack.Value + "/10"; };
            left.Controls.Add(intensityTrack);

            Label objectsLabel = new Label();
            objectsLabel.Text = "Oggetti/immagini naturali";
            objectsLabel.AutoSize = true;
            objectsLabel.Location = new Point(16, 605);
            left.Controls.Add(objectsLabel);

            objectsBox.Text = "bicicletta, casa, denaro, automobile, oggetti enormi";
            objectsBox.Location = new Point(16, 628);
            objectsBox.Size = new Size(left.ClientSize.Width - 32, 28);
            objectsBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            left.Controls.Add(objectsBox);

            Label emotionsLabel = new Label();
            emotionsLabel.Text = "Trigger emotivi";
            emotionsLabel.AutoSize = true;
            emotionsLabel.Location = new Point(16, 665);
            left.Controls.Add(emotionsLabel);

            emotionsBox.Text = "desiderio, sorpresa, comicita, competizione, soddisfazione";
            emotionsBox.Location = new Point(16, 688);
            emotionsBox.Size = new Size(left.ClientSize.Width - 32, 28);
            emotionsBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            left.Controls.Add(emotionsBox);

            GroupBox right = new GroupBox();
            right.Text = "2. Seduta";
            right.Dock = DockStyle.Fill;
            right.Font = new Font("Segoe UI", 11F, FontStyle.Bold);
            split.Panel2.Controls.Add(right);

            Button speakButton = MakeButton("AVVIA VOCE GUIDATA", 16, 30, 190, SpeakButton_Click, true);
            right.Controls.Add(speakButton);
            Button stopButton = MakeButton("STOP", 216, 30, 80, StopButton_Click, false);
            right.Controls.Add(stopButton);
            Button recallButton = MakeButton("TESTAMI", 306, 30, 100, RecallButton_Click, false);
            right.Controls.Add(recallButton);
            Button showButton = MakeButton("VEDI SEDUTA", 416, 30, 120, ShowButton_Click, false);
            right.Controls.Add(showButton);

            outputBox.ReadOnly = true;
            outputBox.Font = new Font("Segoe UI", 11F);
            outputBox.BackColor = Color.White;
            outputBox.Location = new Point(16, 82);
            outputBox.Size = new Size(right.ClientSize.Width - 32, right.ClientSize.Height - 98);
            outputBox.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            outputBox.Text = "Procedura ChatGPT:\r\n1. Incolla il testo.\r\n2. Premi COPIA PROMPT + APRI CHATGPT.\r\n3. Nella chat dedicata premi CTRL+V e invia.\r\n4. Copia la risposta JSON.\r\n5. Torna qui e premi IMPORTA RISPOSTA CHATGPT.";
            right.Controls.Add(outputBox);
        }

        private void WireWorkers()
        {
            ollamaWorker.DoWork += delegate(object sender, DoWorkEventArgs e)
            {
                object[] data = (object[])e.Argument;
                e.Result = ollama.GeneratePlan((string)data[0], (int)data[1], (string)data[2], (string)data[3]);
            };
            ollamaWorker.RunWorkerCompleted += delegate(object sender, RunWorkerCompletedEventArgs e)
            {
                UseWaitCursor = false;
                if (e.Error != null)
                {
                    ShowError("Errore Ollama", e.Error);
                    return;
                }
                currentPlan = (MemoryPlan)e.Result;
                ShowPlan();
                statusLabel.Text = "Seduta generata con Ollama.";
            };

            testWorker.DoWork += delegate(object sender, DoWorkEventArgs e)
            {
                string details;
                if (!ollama.HealthCheck(out details)) throw new InvalidOperationException(details);
                string response = ollama.MiniGenerateTest();
                e.Result = details + " Risposta test: " + response;
            };
            testWorker.RunWorkerCompleted += delegate(object sender, RunWorkerCompletedEventArgs e)
            {
                UseWaitCursor = false;
                if (e.Error != null)
                {
                    ShowError("Test Ollama fallito", e.Error);
                    return;
                }
                statusLabel.Text = "TEST OLLAMA OK.";
                MessageBox.Show((string)e.Result, "Memory Director", MessageBoxButtons.OK, MessageBoxIcon.Information);
            };
        }

        private void ChatButton_Click(object sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(sourceBox.Text))
            {
                statusLabel.Text = "Inserisci prima il testo da memorizzare.";
                return;
            }

            try
            {
                string prompt = MnemonicPromptBuilder.Build(sourceBox.Text, intensityTrack.Value, objectsBox.Text, emotionsBox.Text);
                Clipboard.SetText(prompt);
                ProcessStartInfo startInfo = new ProcessStartInfo(MnemonicPromptBuilder.DedicatedChatUrl);
                startInfo.UseShellExecute = true;
                Process.Start(startInfo);
                statusLabel.Text = "Prompt copiato. Nella conversazione ChatGPT premi CTRL+V e invia.";
                outputBox.Text = "Prompt copiato negli appunti e conversazione dedicata aperta.\r\n\r\nDopo la risposta di ChatGPT:\r\n1. copia tutta la risposta JSON;\r\n2. torna in Memory Director;\r\n3. premi IMPORTA RISPOSTA CHATGPT.";
            }
            catch (Exception ex)
            {
                ShowError("Impossibile aprire ChatGPT", ex);
            }
        }

        private void ImportButton_Click(object sender, EventArgs e)
        {
            try
            {
                if (!Clipboard.ContainsText())
                {
                    throw new InvalidOperationException("Negli appunti non c'e testo. Copia prima la risposta di ChatGPT.");
                }
                string response = Clipboard.GetText();
                currentPlan = PlanParser.Parse(response);
                ShowPlan();
                statusLabel.Text = "Risposta ChatGPT importata correttamente.";
            }
            catch (Exception ex)
            {
                ShowError("Importazione risposta ChatGPT fallita", ex);
            }
        }

        private void ExampleButton_Click(object sender, EventArgs e)
        {
            sourceBox.Text = "La vendita e il contratto che ha per oggetto il trasferimento della proprieta di una cosa o il trasferimento di un altro diritto contro il corrispettivo di un prezzo. La proprieta del bene venduto passa normalmente dal venditore al compratore al momento del consenso fra le parti.";
        }

        private void OllamaButton_Click(object sender, EventArgs e)
        {
            if (ollamaWorker.IsBusy) return;
            if (string.IsNullOrWhiteSpace(sourceBox.Text))
            {
                statusLabel.Text = "Inserisci prima il testo da memorizzare.";
                return;
            }
            UseWaitCursor = true;
            statusLabel.Text = "Ollama sta generando la seduta...";
            outputBox.Text = "Elaborazione locale in corso...";
            ollamaWorker.RunWorkerAsync(new object[] { sourceBox.Text, intensityTrack.Value, objectsBox.Text, emotionsBox.Text });
        }

        private void TestButton_Click(object sender, EventArgs e)
        {
            if (testWorker.IsBusy) return;
            UseWaitCursor = true;
            statusLabel.Text = "Test Ollama in corso...";
            testWorker.RunWorkerAsync();
        }

        private void SpeakButton_Click(object sender, EventArgs e)
        {
            if (currentPlan == null)
            {
                statusLabel.Text = "Prima importa o genera una seduta.";
                return;
            }

            try
            {
                EnsureSapiVoice();
                StringBuilder text = new StringBuilder();
                foreach (string line in currentPlan.guided_movie)
                {
                    if (line == "[pausa]") text.Append(" ... ");
                    else text.Append(line).Append(". ");
                }
                sapiVoiceType.InvokeMember("Speak", BindingFlags.InvokeMethod, null, sapiVoice, new object[] { text.ToString(), 3 });
                statusLabel.Text = "Voce guidata avviata.";
            }
            catch (Exception ex)
            {
                ShowError("Sintesi vocale non disponibile", ex);
            }
        }

        private void StopButton_Click(object sender, EventArgs e)
        {
            try
            {
                if (sapiVoice != null)
                {
                    sapiVoiceType.InvokeMember("Speak", BindingFlags.InvokeMethod, null, sapiVoice, new object[] { string.Empty, 3 });
                }
                statusLabel.Text = "Voce fermata.";
            }
            catch
            {
            }
        }

        private void RecallButton_Click(object sender, EventArgs e)
        {
            if (currentPlan == null)
            {
                statusLabel.Text = "Prima importa o genera una seduta.";
                return;
            }
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("ACTIVE RECALL");
            sb.AppendLine();
            int i = 1;
            foreach (string question in currentPlan.recall_questions)
            {
                sb.AppendLine(i + ". " + question);
                sb.AppendLine();
                i++;
            }
            outputBox.Text = sb.ToString();
            statusLabel.Text = "Rispondi senza rileggere la seduta.";
        }

        private void ShowButton_Click(object sender, EventArgs e)
        {
            if (currentPlan != null) ShowPlan();
        }

        private void EnsureSapiVoice()
        {
            if (sapiVoice != null) return;
            sapiVoiceType = Type.GetTypeFromProgID("SAPI.SpVoice");
            if (sapiVoiceType == null) throw new InvalidOperationException("SAPI.SpVoice non disponibile su questo Windows.");
            sapiVoice = Activator.CreateInstance(sapiVoiceType);
        }

        private void ShowPlan()
        {
            if (currentPlan == null) return;
            StringBuilder sb = new StringBuilder();
            sb.AppendLine(currentPlan.title);
            sb.AppendLine();
            sb.AppendLine("SIGNIFICATO SEMPLICE");
            sb.AppendLine(currentPlan.simple_meaning);
            sb.AppendLine();
            sb.AppendLine("MICRO-CONCETTI");
            int i = 1;
            foreach (string concept in currentPlan.micro_concepts)
            {
                sb.AppendLine(i + ". " + concept);
                i++;
            }
            sb.AppendLine();
            sb.AppendLine("FILM MENTALE");
            foreach (string line in currentPlan.guided_movie)
            {
                sb.AppendLine(line == "[pausa]" ? "     ... pausa ..." : line);
            }
            sb.AppendLine();
            sb.AppendLine("FOTOGRAMMA FINALE");
            sb.AppendLine(currentPlan.final_freeze_frame);
            sb.AppendLine();
            sb.AppendLine("ACTIVE RECALL");
            i = 1;
            foreach (string question in currentPlan.recall_questions)
            {
                sb.AppendLine(i + ". " + question);
                i++;
            }
            outputBox.Text = sb.ToString();
        }

        private void ShowError(string title, Exception ex)
        {
            UseWaitCursor = false;
            string message = ex == null ? "Errore sconosciuto." : ex.Message;
            statusLabel.Text = title + ".";
            outputBox.Text = title + "\r\n\r\n" + message;
            try
            {
                string log = Path.Combine(Path.GetTempPath(), "MemoryDirector_error.txt");
                File.WriteAllText(log, DateTime.Now.ToString("s") + "\r\n" + title + "\r\n" + ex, Encoding.UTF8);
                outputBox.AppendText("\r\n\r\nLog: " + log);
            }
            catch
            {
            }
            MessageBox.Show(message, title, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    internal static class SelfTests
    {
        public static int Run()
        {
            int failures = 0;
            failures += Test("Normalize fenced JSON", delegate
            {
                string input = "```json\n{\"title\":\"x\"}\n```";
                string normalized = PlanParser.NormalizeJson(input);
                if (normalized != "{\"title\":\"x\"}") throw new Exception("NormalizeJson non ha rimosso i fence.");
            });

            failures += Test("Prompt contains guided start", delegate
            {
                string prompt = MnemonicPromptBuilder.Build("vendita", 9, "bicicletta", "sorpresa");
                if (prompt.IndexOf("Chiudi gli occhi. Immagina", StringComparison.Ordinal) < 0) throw new Exception("Prompt incompleto.");
            });

            failures += Test("Dedicated ChatGPT URL", delegate
            {
                if (MnemonicPromptBuilder.DedicatedChatUrl != "https://chatgpt.com/c/6a7a16c8-8a94-83eb-9492-001e95b12c67") throw new Exception("URL ChatGPT dedicato errato.");
            });

            failures += Test("Validate inserts guided start", delegate
            {
                MemoryPlan plan = new MemoryPlan();
                plan.title = "Vendita";
                plan.simple_meaning = "Scambio";
                plan.micro_concepts = new List<string> { "bene" };
                plan.guided_movie = new List<string> { "Vedi una bici." };
                plan.final_freeze_frame = "Bici trasferita.";
                plan.recall_questions = new List<string>();
                PlanParser.ValidatePlan(plan);
                if (!plan.guided_movie[0].StartsWith("Chiudi gli occhi", StringComparison.OrdinalIgnoreCase)) throw new Exception("Apertura guidata non inserita.");
            });

            Console.WriteLine(failures == 0 ? "SELF-TEST OK" : "SELF-TEST FALLITI: " + failures);
            return failures == 0 ? 0 : 1;
        }

        private static int Test(string name, Action action)
        {
            try
            {
                action();
                Console.WriteLine("PASS: " + name);
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine("FAIL: " + name + " - " + ex.Message);
                return 1;
            }
        }
    }
}
