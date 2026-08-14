using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace MemoryDirectorChatGPT
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

    internal static class ChatGptBridge
    {
        public const string ConversationUrl = "https://chatgpt.com/c/6a7e69a9-b370-83ed-9092-86a0dca7d308";

        public static void OpenDedicatedConversation()
        {
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = ConversationUrl;
            psi.UseShellExecute = true;
            Process.Start(psi);
        }

        public static string BuildPrompt(string sourceText, int intensity, string objects, string emotions)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("MEMORY DIRECTOR - SEDUTA MNEMONICA");
            sb.AppendLine();
            sb.AppendLine("Usa il contesto gia presente in QUESTA conversazione dedicata per mantenere coerente il metodo di memorizzazione definito con Joseph.");
            sb.AppendLine("Non fare una spiegazione scolastica: devi costruire una seduta mentale guidata.");
            sb.AppendLine();
            sb.AppendLine("TESTO DA ASSIMILARE:");
            sb.AppendLine(sourceText);
            sb.AppendLine();
            sb.AppendLine("PROFILO MNEMONICO:");
            sb.AppendLine("- intensita PAV: " + intensity + "/10");
            sb.AppendLine("- immagini/oggetti familiari: " + (objects ?? string.Empty));
            sb.AppendLine("- trigger emotivi: " + (emotions ?? string.Empty));
            sb.AppendLine();
            sb.AppendLine("REGOLE:");
            sb.AppendLine("1. Comprendi prima il significato.");
            sb.AppendLine("2. Spacchetta il concetto in massimo 6 micro-concetti che, concatenati, permettono di ricostruire il concetto principale.");
            sb.AppendLine("3. Trasforma le astrazioni in persone, oggetti e azioni concrete.");
            sb.AppendLine("4. La seduta deve iniziare esattamente con: Chiudi gli occhi. Immagina...");
            sb.AppendLine("5. Costruisci il film mentale un elemento alla volta, senza mostrare subito la scena completa.");
            sb.AppendLine("6. Applica PAV: Paradosso, Azione, Vivido.");
            sb.AppendLine("7. Inserisci movimento, sproporzioni, rumori, tatto, temperatura, odori o gusto solo quando sono naturali e utili.");
            sb.AppendLine("8. Inserisci emozione, sorpresa, desiderio, comicita, tensione o soddisfazione quando aiutano a fissare il ricordo.");
            sb.AppendLine("9. Non inventare ricordi personali specifici: invita eventualmente a richiamare una propria esperienza.");
            sb.AppendLine("10. Usa [pausa] come elemento autonomo quando bisogna lasciare tempo alla visualizzazione.");
            sb.AppendLine("11. Termina con un fotogramma finale netto che sintetizzi il concetto.");
            sb.AppendLine("12. Crea 4 domande di active recall senza mostrare subito le risposte.");
            sb.AppendLine("13. Frasi brevi e ritmiche, adatte a una voce guida.");
            sb.AppendLine();
            sb.AppendLine("IMPORTANTE: rispondi SOLO con JSON valido, senza testo prima o dopo, usando esattamente questa struttura:");
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

        public static MemoryPlan ParsePlan(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
                throw new InvalidOperationException("Gli appunti sono vuoti. Copia prima la risposta JSON di ChatGPT.");

            string json = NormalizeJson(raw);
            JavaScriptSerializer serializer = new JavaScriptSerializer();
            MemoryPlan plan;
            try
            {
                plan = serializer.Deserialize<MemoryPlan>(json);
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException("La risposta copiata non contiene JSON valido. Copia la risposta completa di ChatGPT e riprova.", ex);
            }
            ValidatePlan(plan);
            return plan;
        }

        internal static string NormalizeJson(string raw)
        {
            string value = (raw ?? string.Empty).Trim();
            if (value.StartsWith("```json", StringComparison.OrdinalIgnoreCase))
                value = value.Substring(7).TrimStart();
            else if (value.StartsWith("```", StringComparison.Ordinal))
                value = value.Substring(3).TrimStart();

            if (value.EndsWith("```", StringComparison.Ordinal))
                value = value.Substring(0, value.Length - 3).TrimEnd();

            int first = value.IndexOf('{');
            int last = value.LastIndexOf('}');
            if (first >= 0 && last > first)
                value = value.Substring(first, last - first + 1);
            return value.Trim();
        }

        internal static void ValidatePlan(MemoryPlan plan)
        {
            if (plan == null) throw new InvalidOperationException("Seduta nulla.");
            if (string.IsNullOrWhiteSpace(plan.title)) throw new InvalidOperationException("Manca il titolo.");
            if (string.IsNullOrWhiteSpace(plan.simple_meaning)) throw new InvalidOperationException("Manca il significato semplice.");
            if (plan.micro_concepts == null || plan.micro_concepts.Count == 0) throw new InvalidOperationException("Mancano i micro-concetti.");
            if (plan.guided_movie == null || plan.guided_movie.Count == 0) throw new InvalidOperationException("Manca il film mentale.");
            if (plan.guided_movie[0].IndexOf("Chiudi gli occhi", StringComparison.OrdinalIgnoreCase) < 0)
                plan.guided_movie.Insert(0, "Chiudi gli occhi. Immagina...");
            if (string.IsNullOrWhiteSpace(plan.final_freeze_frame)) throw new InvalidOperationException("Manca il fotogramma finale.");
            if (plan.recall_questions == null) plan.recall_questions = new List<string>();
        }
    }

    internal sealed class SapiSpeaker
    {
        private object voice;
        private Type voiceType;

        public void SpeakAsync(string text)
        {
            EnsureVoice();
            voiceType.InvokeMember("Speak", BindingFlags.InvokeMethod, null, voice, new object[] { text, 1 });
        }

        public void Stop()
        {
            if (voice == null || voiceType == null) return;
            try { voiceType.InvokeMember("Speak", BindingFlags.InvokeMethod, null, voice, new object[] { string.Empty, 3 }); } catch { }
        }

        private void EnsureVoice()
        {
            if (voice != null) return;
            voiceType = Type.GetTypeFromProgID("SAPI.SpVoice");
            if (voiceType == null) throw new InvalidOperationException("Sintesi vocale Windows SAPI non disponibile.");
            voice = Activator.CreateInstance(voiceType);
            try { voiceType.InvokeMember("Rate", BindingFlags.SetProperty, null, voice, new object[] { -2 }); } catch { }
        }
    }

    internal sealed class MainForm : Form
    {
        private readonly TextBox sourceBox = new TextBox();
        private readonly RichTextBox outputBox = new RichTextBox();
        private readonly Label statusLabel = new Label();
        private readonly TrackBar intensityTrack = new TrackBar();
        private readonly Label intensityLabel = new Label();
        private readonly TextBox objectsBox = new TextBox();
        private readonly TextBox emotionsBox = new TextBox();
        private readonly Button prepareButton = new Button();
        private readonly Button openButton = new Button();
        private readonly Button importButton = new Button();
        private readonly Button exampleButton = new Button();
        private readonly Button speakButton = new Button();
        private readonly Button stopButton = new Button();
        private readonly Button recallButton = new Button();
        private readonly Button showPlanButton = new Button();
        private readonly SapiSpeaker speaker = new SapiSpeaker();
        private MemoryPlan currentPlan;

        public MainForm()
        {
            Text = "Memory Director - ChatGPT Dedicated";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(1100, 720);
            Size = new Size(1260, 820);
            BackColor = Color.FromArgb(244, 246, 248);
            Font = new Font("Segoe UI", 10F);
            BuildUi();
            WireEvents();
        }

        private void BuildUi()
        {
            Label title = new Label();
            title.Text = "MEMORY DIRECTOR - CHATGPT";
            title.Font = new Font("Segoe UI", 19F, FontStyle.Bold);
            title.AutoSize = true;
            title.Location = new Point(20, 14);
            Controls.Add(title);

            Label subtitle = new Label();
            subtitle.Text = "Conversazione dedicata fissata nel programma";
            subtitle.ForeColor = Color.RoyalBlue;
            subtitle.AutoSize = true;
            subtitle.Location = new Point(23, 52);
            Controls.Add(subtitle);

            SplitContainer split = new SplitContainer();
            split.Location = new Point(20, 82);
            split.Size = new Size(1200, 680);
            split.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            split.SplitterDistance = 580;
            split.BackColor = Color.White;
            Controls.Add(split);

            Label leftTitle = new Label();
            leftTitle.Text = "1. Materiale da memorizzare";
            leftTitle.Font = new Font("Segoe UI", 12F, FontStyle.Bold);
            leftTitle.AutoSize = true;
            leftTitle.Location = new Point(15, 15);
            split.Panel1.Controls.Add(leftTitle);

            sourceBox.Multiline = true;
            sourceBox.ScrollBars = ScrollBars.Vertical;
            sourceBox.AcceptsReturn = true;
            sourceBox.Font = new Font("Segoe UI", 11F);
            sourceBox.Location = new Point(15, 48);
            sourceBox.Size = new Size(545, 300);
            sourceBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            split.Panel1.Controls.Add(sourceBox);

            prepareButton.Text = "PREPARA + APRI CHATGPT";
            prepareButton.Location = new Point(15, 360);
            prepareButton.Size = new Size(200, 40);
            prepareButton.BackColor = Color.FromArgb(17, 24, 39);
            prepareButton.ForeColor = Color.White;
            prepareButton.FlatStyle = FlatStyle.Flat;
            split.Panel1.Controls.Add(prepareButton);

            openButton.Text = "APRI CHAT DEDICATA";
            openButton.Location = new Point(225, 360);
            openButton.Size = new Size(165, 40);
            split.Panel1.Controls.Add(openButton);

            exampleButton.Text = "ESEMPIO: LA VENDITA";
            exampleButton.Location = new Point(400, 360);
            exampleButton.Size = new Size(160, 40);
            split.Panel1.Controls.Add(exampleButton);

            importButton.Text = "IMPORTA RISPOSTA DAGLI APPUNTI";
            importButton.Location = new Point(15, 410);
            importButton.Size = new Size(300, 40);
            importButton.BackColor = Color.DarkGreen;
            importButton.ForeColor = Color.White;
            importButton.FlatStyle = FlatStyle.Flat;
            split.Panel1.Controls.Add(importButton);

            statusLabel.Text = "Pronto. Il motore principale e la conversazione ChatGPT dedicata.";
            statusLabel.Location = new Point(15, 462);
            statusLabel.Size = new Size(545, 45);
            statusLabel.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            split.Panel1.Controls.Add(statusLabel);

            intensityLabel.Text = "Intensita PAV: 9/10";
            intensityLabel.Location = new Point(15, 515);
            intensityLabel.AutoSize = true;
            split.Panel1.Controls.Add(intensityLabel);

            intensityTrack.Minimum = 1;
            intensityTrack.Maximum = 10;
            intensityTrack.Value = 9;
            intensityTrack.TickStyle = TickStyle.None;
            intensityTrack.Location = new Point(15, 538);
            intensityTrack.Size = new Size(545, 35);
            split.Panel1.Controls.Add(intensityTrack);

            Label objectsLabel = new Label();
            objectsLabel.Text = "Oggetti/immagini naturali";
            objectsLabel.Location = new Point(15, 578);
            objectsLabel.AutoSize = true;
            split.Panel1.Controls.Add(objectsLabel);

            objectsBox.Text = "bicicletta, casa, denaro, automobile, oggetti enormi";
            objectsBox.Location = new Point(15, 601);
            objectsBox.Size = new Size(545, 27);
            split.Panel1.Controls.Add(objectsBox);

            Label emotionsLabel = new Label();
            emotionsLabel.Text = "Trigger emotivi";
            emotionsLabel.Location = new Point(15, 636);
            emotionsLabel.AutoSize = true;
            split.Panel1.Controls.Add(emotionsLabel);

            emotionsBox.Text = "desiderio, sorpresa, comicita, competizione, soddisfazione";
            emotionsBox.Location = new Point(15, 659);
            emotionsBox.Size = new Size(545, 27);
            split.Panel1.Controls.Add(emotionsBox);

            Label rightTitle = new Label();
            rightTitle.Text = "2. Seduta importata da ChatGPT";
            rightTitle.Font = new Font("Segoe UI", 12F, FontStyle.Bold);
            rightTitle.AutoSize = true;
            rightTitle.Location = new Point(15, 15);
            split.Panel2.Controls.Add(rightTitle);

            speakButton.Text = "AVVIA VOCE GUIDATA";
            speakButton.Location = new Point(15, 48);
            speakButton.Size = new Size(175, 40);
            speakButton.BackColor = Color.FromArgb(17, 24, 39);
            speakButton.ForeColor = Color.White;
            speakButton.FlatStyle = FlatStyle.Flat;
            split.Panel2.Controls.Add(speakButton);

            stopButton.Text = "STOP";
            stopButton.Location = new Point(200, 48);
            stopButton.Size = new Size(85, 40);
            split.Panel2.Controls.Add(stopButton);

            recallButton.Text = "TESTAMI";
            recallButton.Location = new Point(295, 48);
            recallButton.Size = new Size(90, 40);
            split.Panel2.Controls.Add(recallButton);

            showPlanButton.Text = "VEDI SEDUTA";
            showPlanButton.Location = new Point(395, 48);
            showPlanButton.Size = new Size(110, 40);
            split.Panel2.Controls.Add(showPlanButton);

            outputBox.ReadOnly = true;
            outputBox.Font = new Font("Segoe UI", 11F);
            outputBox.BackColor = Color.White;
            outputBox.Location = new Point(15, 102);
            outputBox.Size = new Size(575, 565);
            outputBox.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            outputBox.Text = "Flusso: 1) prepara il prompt; 2) incollalo nella chat ChatGPT aperta; 3) copia la risposta JSON; 4) torna qui e premi IMPORTA RISPOSTA DAGLI APPUNTI.";
            split.Panel2.Controls.Add(outputBox);
        }

        private void WireEvents()
        {
            intensityTrack.ValueChanged += delegate { intensityLabel.Text = "Intensita PAV: " + intensityTrack.Value + "/10"; };

            exampleButton.Click += delegate
            {
                sourceBox.Text = "La vendita e il contratto che ha per oggetto il trasferimento della proprieta di una cosa o il trasferimento di un altro diritto contro il corrispettivo di un prezzo. La proprieta del bene venduto passa normalmente dal venditore al compratore al momento del consenso fra le parti.";
            };

            openButton.Click += delegate
            {
                try { ChatGptBridge.OpenDedicatedConversation(); statusLabel.Text = "Chat dedicata aperta."; }
                catch (Exception ex) { ShowError(ex); }
            };

            prepareButton.Click += delegate
            {
                if (string.IsNullOrWhiteSpace(sourceBox.Text))
                {
                    statusLabel.Text = "Inserisci prima un testo.";
                    return;
                }

                try
                {
                    string prompt = ChatGptBridge.BuildPrompt(sourceBox.Text, intensityTrack.Value, objectsBox.Text, emotionsBox.Text);
                    Clipboard.SetText(prompt);
                    ChatGptBridge.OpenDedicatedConversation();
                    statusLabel.Text = "Prompt copiato. Nella chat premi CTRL+V e INVIO. Poi copia la risposta JSON e torna qui.";
                    outputBox.Text = "PROMPT COPIATO NEGLI APPUNTI.\r\n\r\nLa conversazione ChatGPT dedicata e stata aperta.\r\nPremi CTRL+V, poi INVIO.\r\nQuando ChatGPT risponde, copia tutta la risposta e premi IMPORTA RISPOSTA DAGLI APPUNTI.";
                }
                catch (Exception ex) { ShowError(ex); }
            };

            importButton.Click += delegate
            {
                try
                {
                    string raw = Clipboard.ContainsText() ? Clipboard.GetText() : string.Empty;
                    currentPlan = ChatGptBridge.ParsePlan(raw);
                    outputBox.Text = FormatPlan(currentPlan);
                    statusLabel.Text = "Risposta ChatGPT importata. Seduta pronta.";
                }
                catch (Exception ex) { ShowError(ex); }
            };

            showPlanButton.Click += delegate
            {
                if (currentPlan == null) { statusLabel.Text = "Importa prima una risposta da ChatGPT."; return; }
                outputBox.Text = FormatPlan(currentPlan);
            };

            recallButton.Click += delegate
            {
                if (currentPlan == null) { statusLabel.Text = "Importa prima una risposta da ChatGPT."; return; }
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("ACTIVE RECALL");
                sb.AppendLine();
                int i = 1;
                foreach (string q in currentPlan.recall_questions)
                {
                    sb.AppendLine(i + ". " + q);
                    sb.AppendLine();
                    i++;
                }
                outputBox.Text = sb.ToString();
                statusLabel.Text = "Rispondi senza rileggere la seduta.";
            };

            speakButton.Click += delegate
            {
                if (currentPlan == null) { statusLabel.Text = "Importa prima una risposta da ChatGPT."; return; }
                try
                {
                    speaker.Stop();
                    foreach (string line in currentPlan.guided_movie)
                    {
                        if (line == "[pausa]") speaker.SpeakAsync("...");
                        else speaker.SpeakAsync(line);
                    }
                    statusLabel.Text = "Voce guidata avviata.";
                }
                catch (Exception ex) { ShowError(ex); }
            };

            stopButton.Click += delegate { speaker.Stop(); statusLabel.Text = "Voce fermata."; };
        }

        private void ShowError(Exception ex)
        {
            statusLabel.Text = "ERRORE";
            outputBox.Text = ex.Message;
            MessageBox.Show(ex.Message, "Memory Director", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }

        private static string FormatPlan(MemoryPlan plan)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine(plan.title);
            sb.AppendLine();
            sb.AppendLine("SIGNIFICATO SEMPLICE");
            sb.AppendLine(plan.simple_meaning);
            sb.AppendLine();
            sb.AppendLine("MICRO-CONCETTI");
            for (int i = 0; i < plan.micro_concepts.Count; i++) sb.AppendLine((i + 1) + ". " + plan.micro_concepts[i]);
            sb.AppendLine();
            sb.AppendLine("FILM MENTALE");
            foreach (string line in plan.guided_movie) sb.AppendLine(line == "[pausa]" ? "    ... pausa ..." : line);
            sb.AppendLine();
            sb.AppendLine("FOTOGRAMMA FINALE");
            sb.AppendLine(plan.final_freeze_frame);
            sb.AppendLine();
            sb.AppendLine("ACTIVE RECALL");
            for (int i = 0; i < plan.recall_questions.Count; i++) sb.AppendLine((i + 1) + ". " + plan.recall_questions[i]);
            return sb.ToString();
        }
    }

    internal static class SelfTests
    {
        public static int Run()
        {
            int failures = 0;
            failures += Test("Dedicated URL", ChatGptBridge.ConversationUrl == "https://chatgpt.com/c/6a7e69a9-b370-83ed-9092-86a0dca7d308");

            string prompt = ChatGptBridge.BuildPrompt("La vendita trasferisce la proprieta contro un prezzo.", 9, "bicicletta", "sorpresa");
            failures += Test("Prompt contains source", prompt.IndexOf("La vendita trasferisce", StringComparison.Ordinal) >= 0);
            failures += Test("Prompt requires guided opening", prompt.IndexOf("Chiudi gli occhi. Immagina", StringComparison.Ordinal) >= 0);
            failures += Test("Prompt requires JSON", prompt.IndexOf("SOLO con JSON valido", StringComparison.Ordinal) >= 0);

            string fenced = "```json\n{\"title\":\"Vendita\",\"simple_meaning\":\"Scambio\",\"micro_concepts\":[\"bene\",\"prezzo\"],\"guided_movie\":[\"Chiudi gli occhi. Immagina...\",\"Una bici enorme\"],\"final_freeze_frame\":\"Bici da una parte, soldi dall'altra\",\"recall_questions\":[\"Chi riceve il bene?\"]}\n```";
            try
            {
                MemoryPlan plan = ChatGptBridge.ParsePlan(fenced);
                failures += Test("Parse fenced JSON", plan != null && plan.title == "Vendita" && plan.guided_movie.Count == 2);
            }
            catch (Exception ex)
            {
                Console.WriteLine("FAIL Parse fenced JSON: " + ex.Message);
                failures++;
            }

            Console.WriteLine(failures == 0 ? "ALL SELF-TESTS PASSED" : (failures + " SELF-TESTS FAILED"));
            return failures == 0 ? 0 : 1;
        }

        private static int Test(string name, bool ok)
        {
            Console.WriteLine((ok ? "PASS " : "FAIL ") + name);
            return ok ? 0 : 1;
        }
    }
}
