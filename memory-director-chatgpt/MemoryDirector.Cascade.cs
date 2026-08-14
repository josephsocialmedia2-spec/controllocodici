using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace MemoryDirectorChatGPT
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            if (args != null && args.Length > 0 &&
                string.Equals(args[0], "--self-test", StringComparison.OrdinalIgnoreCase))
            {
                Environment.Exit(SelfTests.Run());
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    internal sealed class CascadeBranch
    {
        public string branch { get; set; }
        public List<string> details { get; set; }
        public string example { get; set; }
    }

    internal sealed class MnemonicAnchor
    {
        public string concept { get; set; }
        public string image { get; set; }
    }

    internal sealed class MemoryPlan
    {
        public string title { get; set; }
        public string key_question { get; set; }
        public string core_concept { get; set; }
        public List<CascadeBranch> cascade_branches { get; set; }
        public List<MnemonicAnchor> mnemonic_anchors { get; set; }
        public List<string> guided_movie { get; set; }
        public string final_freeze_frame { get; set; }
        public List<string> recall_questions { get; set; }
        public string simple_meaning { get; set; }
        public List<string> micro_concepts { get; set; }
    }

    internal sealed class VoiceChoice
    {
        public int Index { get; private set; }
        public string Name { get; private set; }

        public VoiceChoice(int index, string name)
        {
            Index = index;
            Name = string.IsNullOrWhiteSpace(name) ? ("Voce " + (index + 1)) : name;
        }

        public override string ToString()
        {
            return Name;
        }
    }

    internal sealed class VoiceSettings
    {
        public int VoiceIndex { get; set; }
        public int Rate { get; set; }
        public int Volume { get; set; }
        public int PauseMilliseconds { get; set; }

        public VoiceSettings()
        {
            VoiceIndex = 0;
            Rate = -2;
            Volume = 100;
            PauseMilliseconds = 1200;
        }

        public static int ClampRate(int value)
        {
            if (value < -10) return -10;
            if (value > 10) return 10;
            return value;
        }

        public static int ClampVolume(int value)
        {
            if (value < 0) return 0;
            if (value > 100) return 100;
            return value;
        }

        public static int ClampPause(int value)
        {
            if (value < 300) return 300;
            if (value > 4000) return 4000;
            return value;
        }
    }

    internal static class ChatGptBridge
    {
        public const string ConversationUrl =
            "https://chatgpt.com/c/6a7e69a9-b370-83ed-9092-86a0dca7d308";

        public static void OpenDedicatedConversation()
        {
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = ConversationUrl;
            psi.UseShellExecute = true;
            Process.Start(psi);
        }

        public static string BuildPrompt(string sourceText, int intensity, string objects, string emotions)
        {
            if (string.IsNullOrWhiteSpace(sourceText))
                throw new ArgumentException("Inserisci prima il testo da memorizzare.");

            StringBuilder sb = new StringBuilder();
            sb.AppendLine("MEMORY DIRECTOR - SCHEMA A CASCATA + MEMORIZZAZIONE");
            sb.AppendLine();
            sb.AppendLine("Usa il contesto gia presente in QUESTA conversazione dedicata per mantenere coerente il metodo definito con Joseph.");
            sb.AppendLine("OBIETTIVO PRINCIPALE: NON creare una spiegazione lunga e NON raccontare tutto il testo come un film.");
            sb.AppendLine("Prima comprendi e comprimi il materiale in uno SCHEMA A CASCATA; solo dopo crea pochi ganci mnemonici e una guida audio breve.");
            sb.AppendLine();
            sb.AppendLine("TESTO DA ASSIMILARE:");
            sb.AppendLine(sourceText);
            sb.AppendLine();
            sb.AppendLine("PROFILO MNEMONICO:");
            sb.AppendLine("- intensita PAV: " + intensity + "/10");
            sb.AppendLine("- immagini/oggetti familiari: " + (objects ?? string.Empty));
            sb.AppendLine("- trigger emotivi: " + (emotions ?? string.Empty));
            sb.AppendLine();
            sb.AppendLine("METODO A CASCATA OBBLIGATORIO:");
            sb.AppendLine("1. Trasforma il titolo in una DOMANDA CHIAVE da esame.");
            sb.AppendLine("2. Scrivi il CONCETTO CENTRALE in una sola frase molto breve.");
            sb.AppendLine("3. Crea da 3 a 5 RAMI principali. Ogni ramo deve avere un titolo di poche parole.");
            sb.AppendLine("4. Sotto ogni ramo inserisci massimo 3 dettagli essenziali, in forma di parole chiave o frasi telegrafiche.");
            sb.AppendLine("5. Inserisci un esempio solo quando rende davvero concreto il ramo.");
            sb.AppendLine("6. Usa collegamenti logici e formule sintetiche: ->, =, salvo, se/allora, causa/effetto.");
            sb.AppendLine("7. Niente paragrafi nei rami. Ogni dettaglio deve restare breve e visivo.");
            sb.AppendLine();
            sb.AppendLine("MEMORIZZAZIONE:");
            sb.AppendLine("8. Individua massimo 3 punti realmente difficili da ricordare: articoli, eccezioni, distinzioni o sequenze.");
            sb.AppendLine("9. Solo per quei punti crea un gancio PAV: Paradosso, Azione, Vivido.");
            sb.AppendLine("10. Le immagini devono essere concrete, forti e diverse fra loro.");
            sb.AppendLine("11. Non inventare ricordi personali specifici.");
            sb.AppendLine();
            sb.AppendLine("AUDIO GUIDATO - DEVE ESSERE BREVE:");
            sb.AppendLine("12. La voce NON deve leggere tutto lo schema.");
            sb.AppendLine("13. Deve far visualizzare: concetto centrale -> rami principali -> massimo 3 ganci difficili.");
            sb.AppendLine("14. Durata obiettivo: 60-90 secondi.");
            sb.AppendLine("15. Massimo 14 frasi parlate e massimo 5 elementi [pausa].");
            sb.AppendLine("16. La prima frase deve essere esattamente: Chiudi gli occhi. Immagina...");
            sb.AppendLine("17. Usa [pausa] come elemento autonomo per lasciare vero tempo alla visualizzazione.");
            sb.AppendLine("18. Termina con un solo fotogramma finale che faccia vedere la struttura a cascata.");
            sb.AppendLine();
            sb.AppendLine("ACTIVE RECALL:");
            sb.AppendLine("19. Crea 4 domande che seguano la cascata: domanda chiave, concetto centrale, rami, eccezioni.");
            sb.AppendLine();
            sb.AppendLine("IMPORTANTE: rispondi SOLO con JSON valido, senza testo prima o dopo, usando ESATTAMENTE questa struttura:");
            sb.AppendLine("{");
            sb.AppendLine("  \"title\": \"...\",");
            sb.AppendLine("  \"key_question\": \"...\",");
            sb.AppendLine("  \"core_concept\": \"...\",");
            sb.AppendLine("  \"cascade_branches\": [");
            sb.AppendLine("    {\"branch\":\"...\", \"details\":[\"...\",\"...\"], \"example\":\"...\"}");
            sb.AppendLine("  ],");
            sb.AppendLine("  \"mnemonic_anchors\": [");
            sb.AppendLine("    {\"concept\":\"...\", \"image\":\"...\"}");
            sb.AppendLine("  ],");
            sb.AppendLine("  \"guided_movie\": [\"Chiudi gli occhi. Immagina...\", \"[pausa]\", \"...\"],");
            sb.AppendLine("  \"final_freeze_frame\": \"...\",");
            sb.AppendLine("  \"recall_questions\": [\"...\",\"...\",\"...\",\"...\"]");
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

            NormalizeLegacyPlan(plan);
            ValidatePlan(plan);
            return plan;
        }

        internal static string NormalizeJson(string raw)
        {
            string value = (raw ?? string.Empty).Trim();
            if (value.StartsWith("```json", StringComparison.OrdinalIgnoreCase)) value = value.Substring(7).TrimStart();
            else if (value.StartsWith("```", StringComparison.Ordinal)) value = value.Substring(3).TrimStart();
            if (value.EndsWith("```", StringComparison.Ordinal)) value = value.Substring(0, value.Length - 3).TrimEnd();
            int first = value.IndexOf('{');
            int last = value.LastIndexOf('}');
            if (first >= 0 && last > first) value = value.Substring(first, last - first + 1);
            return value.Trim();
        }

        private static void NormalizeLegacyPlan(MemoryPlan plan)
        {
            if (plan == null) return;
            if (string.IsNullOrWhiteSpace(plan.core_concept)) plan.core_concept = plan.simple_meaning;
            if (string.IsNullOrWhiteSpace(plan.key_question)) plan.key_question = plan.title;
            if ((plan.cascade_branches == null || plan.cascade_branches.Count == 0) && plan.micro_concepts != null && plan.micro_concepts.Count > 0)
            {
                plan.cascade_branches = new List<CascadeBranch>();
                for (int i = 0; i < plan.micro_concepts.Count && i < 5; i++)
                    plan.cascade_branches.Add(new CascadeBranch { branch = "Punto " + (i + 1), details = new List<string> { plan.micro_concepts[i] }, example = string.Empty });
            }
            if (plan.mnemonic_anchors == null) plan.mnemonic_anchors = new List<MnemonicAnchor>();
        }

        internal static void ValidatePlan(MemoryPlan plan)
        {
            if (plan == null) throw new InvalidOperationException("Seduta nulla.");
            if (string.IsNullOrWhiteSpace(plan.title)) throw new InvalidOperationException("Manca il titolo.");
            if (string.IsNullOrWhiteSpace(plan.key_question)) throw new InvalidOperationException("Manca la domanda chiave.");
            if (string.IsNullOrWhiteSpace(plan.core_concept)) throw new InvalidOperationException("Manca il concetto centrale.");
            if (plan.cascade_branches == null || plan.cascade_branches.Count == 0) throw new InvalidOperationException("Manca lo schema a cascata.");
            if (plan.cascade_branches.Count > 5) plan.cascade_branches.RemoveRange(5, plan.cascade_branches.Count - 5);
            foreach (CascadeBranch branch in plan.cascade_branches)
            {
                if (branch.details == null) branch.details = new List<string>();
                if (branch.details.Count > 3) branch.details.RemoveRange(3, branch.details.Count - 3);
            }
            if (plan.mnemonic_anchors == null) plan.mnemonic_anchors = new List<MnemonicAnchor>();
            if (plan.mnemonic_anchors.Count > 3) plan.mnemonic_anchors.RemoveRange(3, plan.mnemonic_anchors.Count - 3);
            if (plan.guided_movie == null || plan.guided_movie.Count == 0) throw new InvalidOperationException("Manca la guida mentale.");
            if (plan.guided_movie[0].IndexOf("Chiudi gli occhi", StringComparison.OrdinalIgnoreCase) < 0) plan.guided_movie.Insert(0, "Chiudi gli occhi. Immagina...");
            TrimGuidedMovie(plan.guided_movie);
            if (string.IsNullOrWhiteSpace(plan.final_freeze_frame)) throw new InvalidOperationException("Manca il fotogramma finale.");
            if (plan.recall_questions == null) plan.recall_questions = new List<string>();
            if (plan.recall_questions.Count > 4) plan.recall_questions.RemoveRange(4, plan.recall_questions.Count - 4);
        }

        private static void TrimGuidedMovie(List<string> lines)
        {
            List<string> compact = new List<string>();
            int spoken = 0;
            int pauses = 0;
            foreach (string line in lines)
            {
                string value = (line ?? string.Empty).Trim();
                if (value.Length == 0) continue;
                if (string.Equals(value, "[pausa]", StringComparison.OrdinalIgnoreCase))
                {
                    if (pauses < 5) { compact.Add("[pausa]"); pauses++; }
                }
                else if (spoken < 14) { compact.Add(value); spoken++; }
            }
            lines.Clear();
            lines.AddRange(compact);
        }
    }

    internal sealed class SapiSpeaker
    {
        private readonly object sync = new object();
        private volatile bool stopRequested;
        private object activeVoice;
        private Type activeVoiceType;

        public List<VoiceChoice> GetVoices()
        {
            List<VoiceChoice> result = new List<VoiceChoice>();
            Type voiceType = Type.GetTypeFromProgID("SAPI.SpVoice");
            if (voiceType == null) return result;
            object voice = null;
            object tokens = null;
            try
            {
                voice = Activator.CreateInstance(voiceType);
                tokens = voiceType.InvokeMember("GetVoices", BindingFlags.InvokeMethod, null, voice, new object[] { "", "" });
                Type tokensType = tokens.GetType();
                int count = Convert.ToInt32(tokensType.InvokeMember("Count", BindingFlags.GetProperty, null, tokens, null));
                for (int i = 0; i < count; i++)
                {
                    object token = tokensType.InvokeMember("Item", BindingFlags.GetProperty, null, tokens, new object[] { i });
                    result.Add(new VoiceChoice(i, GetTokenDescription(token, i)));
                    ReleaseComObject(token);
                }
            }
            catch { }
            finally { ReleaseComObject(tokens); ReleaseComObject(voice); }
            return result;
        }

        public void SpeakPreviewAsync(VoiceSettings settings)
        {
            SpeakPlanAsync(new List<string> { "Chiudi gli occhi.", "[pausa]", "Immagina il concetto al centro.", "[pausa]", "Da quel concetto partono pochi rami chiari.", "Questa e la voce che guidera la tua seduta." }, settings);
        }

        public void SpeakPlanAsync(IList<string> lines, VoiceSettings settings)
        {
            if (lines == null || lines.Count == 0) throw new ArgumentException("Non ci sono frasi da leggere.");
            Stop();
            VoiceSettings safe = new VoiceSettings { VoiceIndex = settings == null ? 0 : settings.VoiceIndex, Rate = VoiceSettings.ClampRate(settings == null ? -2 : settings.Rate), Volume = VoiceSettings.ClampVolume(settings == null ? 100 : settings.Volume), PauseMilliseconds = VoiceSettings.ClampPause(settings == null ? 1200 : settings.PauseMilliseconds) };
            List<string> copy = new List<string>();
            foreach (string line in lines) copy.Add(line ?? string.Empty);
            stopRequested = false;
            Thread worker = new Thread(delegate() { RunSpeech(copy, safe); });
            worker.IsBackground = true;
            worker.Name = "MemoryDirectorSpeech";
            worker.SetApartmentState(ApartmentState.STA);
            worker.Start();
        }

        public void Stop()
        {
            stopRequested = true;
            lock (sync)
            {
                if (activeVoice != null && activeVoiceType != null)
                {
                    try { activeVoiceType.InvokeMember("Speak", BindingFlags.InvokeMethod, null, activeVoice, new object[] { string.Empty, 3 }); } catch { }
                }
            }
        }

        private void RunSpeech(IList<string> lines, VoiceSettings settings)
        {
            Type voiceType = Type.GetTypeFromProgID("SAPI.SpVoice");
            if (voiceType == null) return;
            object voice = null;
            object tokens = null;
            object selectedToken = null;
            try
            {
                voice = Activator.CreateInstance(voiceType);
                lock (sync) { activeVoice = voice; activeVoiceType = voiceType; }
                SetPropertySafe(voiceType, voice, "Rate", settings.Rate);
                SetPropertySafe(voiceType, voice, "Volume", settings.Volume);
                try
                {
                    tokens = voiceType.InvokeMember("GetVoices", BindingFlags.InvokeMethod, null, voice, new object[] { "", "" });
                    Type tokensType = tokens.GetType();
                    int count = Convert.ToInt32(tokensType.InvokeMember("Count", BindingFlags.GetProperty, null, tokens, null));
                    if (count > 0)
                    {
                        int index = settings.VoiceIndex;
                        if (index < 0) index = 0;
                        if (index >= count) index = count - 1;
                        selectedToken = tokensType.InvokeMember("Item", BindingFlags.GetProperty, null, tokens, new object[] { index });
                        voiceType.InvokeMember("Voice", BindingFlags.SetProperty, null, voice, new object[] { selectedToken });
                    }
                }
                catch { }
                foreach (string raw in lines)
                {
                    if (stopRequested) break;
                    string line = (raw ?? string.Empty).Trim();
                    if (string.Equals(line, "[pausa]", StringComparison.OrdinalIgnoreCase)) { WaitPause(settings.PauseMilliseconds); continue; }
                    if (line.Length == 0) continue;
                    voiceType.InvokeMember("Speak", BindingFlags.InvokeMethod, null, voice, new object[] { line, 0 });
                    WaitPause(120);
                }
            }
            catch { }
            finally
            {
                lock (sync) { activeVoice = null; activeVoiceType = null; }
                ReleaseComObject(selectedToken); ReleaseComObject(tokens); ReleaseComObject(voice);
            }
        }

        private void WaitPause(int milliseconds)
        {
            int elapsed = 0;
            while (!stopRequested && elapsed < milliseconds)
            {
                int step = Math.Min(100, milliseconds - elapsed);
                Thread.Sleep(step);
                elapsed += step;
            }
        }

        private static void SetPropertySafe(Type type, object target, string propertyName, object value)
        {
            try { type.InvokeMember(propertyName, BindingFlags.SetProperty, null, target, new object[] { value }); } catch { }
        }

        private static string GetTokenDescription(object token, int index)
        {
            if (token == null) return "Voce " + (index + 1);
            try
            {
                Type tokenType = token.GetType();
                object description = tokenType.InvokeMember("GetDescription", BindingFlags.InvokeMethod, null, token, null);
                string text = Convert.ToString(description);
                return string.IsNullOrWhiteSpace(text) ? ("Voce " + (index + 1)) : text;
            }
            catch { return "Voce " + (index + 1); }
        }

        private static void ReleaseComObject(object value)
        {
            if (value == null) return;
            try { if (System.Runtime.InteropServices.Marshal.IsComObject(value)) System.Runtime.InteropServices.Marshal.FinalReleaseComObject(value); } catch { }
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
        private readonly ComboBox voiceCombo = new ComboBox();
        private readonly Button previewVoiceButton = new Button();
        private readonly TrackBar rateTrack = new TrackBar();
        private readonly TrackBar volumeTrack = new TrackBar();
        private readonly TrackBar pauseTrack = new TrackBar();
        private readonly Label rateLabel = new Label();
        private readonly Label volumeLabel = new Label();
        private readonly Label pauseLabel = new Label();
        private readonly SapiSpeaker speaker = new SapiSpeaker();
        private MemoryPlan currentPlan;

        public MainForm()
        {
            Text = "Memory Director - ChatGPT - Schema a Cascata";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(1180, 760);
            Size = new Size(1320, 860);
            BackColor = Color.FromArgb(244, 246, 248);
            Font = new Font("Segoe UI", 10F);
            BuildUi();
            WireEvents();
            LoadVoices();
        }

        private void BuildUi()
        {
            Label title = new Label(); title.Text = "MEMORY DIRECTOR - SCHEMA A CASCATA"; title.Font = new Font("Segoe UI", 19F, FontStyle.Bold); title.AutoSize = true; title.Location = new Point(20, 14); Controls.Add(title);
            Label subtitle = new Label(); subtitle.Text = "ChatGPT dedicato -> schema gerarchico -> pochi ganci -> audio breve"; subtitle.ForeColor = Color.RoyalBlue; subtitle.AutoSize = true; subtitle.Location = new Point(23, 52); Controls.Add(subtitle);
            SplitContainer split = new SplitContainer(); split.Location = new Point(20, 82); split.Size = new Size(1260, 720); split.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right; split.SplitterDistance = 585; split.BackColor = Color.White; Controls.Add(split);
            BuildLeftPanel(split.Panel1); BuildRightPanel(split.Panel2);
        }

        private void BuildLeftPanel(Control panel)
        {
            Label leftTitle = new Label(); leftTitle.Text = "1. Materiale da trasformare in schema"; leftTitle.Font = new Font("Segoe UI", 12F, FontStyle.Bold); leftTitle.AutoSize = true; leftTitle.Location = new Point(15, 15); panel.Controls.Add(leftTitle);
            sourceBox.Multiline = true; sourceBox.ScrollBars = ScrollBars.Vertical; sourceBox.AcceptsReturn = true; sourceBox.Font = new Font("Segoe UI", 11F); sourceBox.Location = new Point(15, 48); sourceBox.Size = new Size(550, 295); sourceBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right; panel.Controls.Add(sourceBox);
            prepareButton.Text = "PREPARA + APRI CHATGPT"; prepareButton.Location = new Point(15, 355); prepareButton.Size = new Size(205, 40); prepareButton.BackColor = Color.FromArgb(17, 24, 39); prepareButton.ForeColor = Color.White; prepareButton.FlatStyle = FlatStyle.Flat; panel.Controls.Add(prepareButton);
            openButton.Text = "APRI CHAT DEDICATA"; openButton.Location = new Point(230, 355); openButton.Size = new Size(165, 40); panel.Controls.Add(openButton);
            exampleButton.Text = "ESEMPIO"; exampleButton.Location = new Point(405, 355); exampleButton.Size = new Size(160, 40); panel.Controls.Add(exampleButton);
            importButton.Text = "IMPORTA RISPOSTA DAGLI APPUNTI"; importButton.Location = new Point(15, 405); importButton.Size = new Size(300, 40); importButton.BackColor = Color.DarkGreen; importButton.ForeColor = Color.White; importButton.FlatStyle = FlatStyle.Flat; panel.Controls.Add(importButton);
            statusLabel.Text = "Pronto. Lo schema a cascata e il contenuto principale; l'audio serve solo a fissarlo."; statusLabel.Location = new Point(15, 455); statusLabel.Size = new Size(550, 50); statusLabel.Font = new Font("Segoe UI", 9F, FontStyle.Bold); panel.Controls.Add(statusLabel);
            intensityLabel.Text = "Intensita PAV: 9/10"; intensityLabel.Location = new Point(15, 512); intensityLabel.AutoSize = true; panel.Controls.Add(intensityLabel);
            intensityTrack.Minimum = 1; intensityTrack.Maximum = 10; intensityTrack.Value = 9; intensityTrack.TickStyle = TickStyle.None; intensityTrack.Location = new Point(15, 535); intensityTrack.Size = new Size(550, 35); panel.Controls.Add(intensityTrack);
            Label objectsLabel = new Label(); objectsLabel.Text = "Oggetti/immagini naturali"; objectsLabel.Location = new Point(15, 575); objectsLabel.AutoSize = true; panel.Controls.Add(objectsLabel);
            objectsBox.Text = "bicicletta, casa, denaro, automobile, oggetti enormi"; objectsBox.Location = new Point(15, 598); objectsBox.Size = new Size(550, 27); panel.Controls.Add(objectsBox);
            Label emotionsLabel = new Label(); emotionsLabel.Text = "Trigger emotivi"; emotionsLabel.Location = new Point(15, 635); emotionsLabel.AutoSize = true; panel.Controls.Add(emotionsLabel);
            emotionsBox.Text = "desiderio, sorpresa, comicita, competizione, soddisfazione"; emotionsBox.Location = new Point(15, 658); emotionsBox.Size = new Size(550, 27); panel.Controls.Add(emotionsBox);
        }

        private void BuildRightPanel(Control panel)
        {
            Label rightTitle = new Label(); rightTitle.Text = "2. Schema a cascata + memoria"; rightTitle.Font = new Font("Segoe UI", 12F, FontStyle.Bold); rightTitle.AutoSize = true; rightTitle.Location = new Point(15, 15); panel.Controls.Add(rightTitle);
            speakButton.Text = "AVVIA AUDIO"; speakButton.Location = new Point(15, 47); speakButton.Size = new Size(125, 38); speakButton.BackColor = Color.FromArgb(17, 24, 39); speakButton.ForeColor = Color.White; speakButton.FlatStyle = FlatStyle.Flat; panel.Controls.Add(speakButton);
            stopButton.Text = "STOP"; stopButton.Location = new Point(150, 47); stopButton.Size = new Size(75, 38); panel.Controls.Add(stopButton);
            recallButton.Text = "TESTAMI"; recallButton.Location = new Point(235, 47); recallButton.Size = new Size(85, 38); panel.Controls.Add(recallButton);
            showPlanButton.Text = "VEDI SCHEMA"; showPlanButton.Location = new Point(330, 47); showPlanButton.Size = new Size(115, 38); panel.Controls.Add(showPlanButton);
            GroupBox voiceBox = new GroupBox(); voiceBox.Text = "Voce guidata"; voiceBox.Location = new Point(15, 95); voiceBox.Size = new Size(625, 145); voiceBox.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right; panel.Controls.Add(voiceBox);
            Label voiceLabel = new Label(); voiceLabel.Text = "Voce"; voiceLabel.Location = new Point(12, 27); voiceLabel.AutoSize = true; voiceBox.Controls.Add(voiceLabel);
            voiceCombo.DropDownStyle = ComboBoxStyle.DropDownList; voiceCombo.Location = new Point(58, 23); voiceCombo.Size = new Size(300, 27); voiceBox.Controls.Add(voiceCombo);
            previewVoiceButton.Text = "ANTEPRIMA"; previewVoiceButton.Location = new Point(370, 22); previewVoiceButton.Size = new Size(105, 30); voiceBox.Controls.Add(previewVoiceButton);
            rateLabel.Text = "Velocita: -2"; rateLabel.Location = new Point(12, 63); rateLabel.AutoSize = true; voiceBox.Controls.Add(rateLabel);
            rateTrack.Minimum = -6; rateTrack.Maximum = 4; rateTrack.Value = -2; rateTrack.TickStyle = TickStyle.None; rateTrack.Location = new Point(105, 56); rateTrack.Size = new Size(175, 30); voiceBox.Controls.Add(rateTrack);
            volumeLabel.Text = "Volume: 100"; volumeLabel.Location = new Point(295, 63); volumeLabel.AutoSize = true; voiceBox.Controls.Add(volumeLabel);
            volumeTrack.Minimum = 20; volumeTrack.Maximum = 100; volumeTrack.Value = 100; volumeTrack.TickStyle = TickStyle.None; volumeTrack.Location = new Point(390, 56); volumeTrack.Size = new Size(185, 30); voiceBox.Controls.Add(volumeTrack);
            pauseLabel.Text = "Pausa: 1.2 s"; pauseLabel.Location = new Point(12, 105); pauseLabel.AutoSize = true; voiceBox.Controls.Add(pauseLabel);
            pauseTrack.Minimum = 5; pauseTrack.Maximum = 25; pauseTrack.Value = 12; pauseTrack.TickStyle = TickStyle.None; pauseTrack.Location = new Point(105, 98); pauseTrack.Size = new Size(240, 30); voiceBox.Controls.Add(pauseTrack);
            Label note = new Label(); note.Text = "[pausa] = silenzio reale. L'audio non legge tutto lo schema."; note.ForeColor = Color.DimGray; note.Location = new Point(365, 103); note.Size = new Size(235, 35); voiceBox.Controls.Add(note);
            outputBox.ReadOnly = true; outputBox.Font = new Font("Consolas", 10.5F); outputBox.BackColor = Color.White; outputBox.Location = new Point(15, 252); outputBox.Size = new Size(625, 450); outputBox.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right; outputBox.Text = "Flusso:\r\n1) Prepara e apri ChatGPT.\r\n2) Incolla il prompt e invialo.\r\n3) Copia il JSON.\r\n4) Importalo qui.\r\n\r\nIl risultato principale sara uno schema a cascata breve."; panel.Controls.Add(outputBox);
        }

        private void LoadVoices()
        {
            try
            {
                List<VoiceChoice> voices = speaker.GetVoices(); voiceCombo.Items.Clear(); foreach (VoiceChoice voice in voices) voiceCombo.Items.Add(voice);
                if (voiceCombo.Items.Count > 0) voiceCombo.SelectedIndex = 0; else { voiceCombo.Items.Add(new VoiceChoice(0, "Voce predefinita Windows")); voiceCombo.SelectedIndex = 0; }
            }
            catch { voiceCombo.Items.Add(new VoiceChoice(0, "Voce predefinita Windows")); voiceCombo.SelectedIndex = 0; }
        }

        private VoiceSettings CurrentVoiceSettings()
        {
            VoiceChoice choice = voiceCombo.SelectedItem as VoiceChoice;
            return new VoiceSettings { VoiceIndex = choice == null ? 0 : choice.Index, Rate = rateTrack.Value, Volume = volumeTrack.Value, PauseMilliseconds = pauseTrack.Value * 100 };
        }

        private void WireEvents()
        {
            intensityTrack.ValueChanged += delegate { intensityLabel.Text = "Intensita PAV: " + intensityTrack.Value + "/10"; };
            rateTrack.ValueChanged += delegate { rateLabel.Text = "Velocita: " + rateTrack.Value; };
            volumeTrack.ValueChanged += delegate { volumeLabel.Text = "Volume: " + volumeTrack.Value; };
            pauseTrack.ValueChanged += delegate { pauseLabel.Text = "Pausa: " + (pauseTrack.Value / 10.0).ToString("0.0") + " s"; };
            previewVoiceButton.Click += delegate { try { speaker.SpeakPreviewAsync(CurrentVoiceSettings()); statusLabel.Text = "Anteprima voce avviata."; } catch (Exception ex) { ShowError(ex); } };
            exampleButton.Click += delegate { sourceBox.Text = "Regime giuridico delle pertinenze. L'art. 818 c.c. stabilisce che la pertinenza segue normalmente il regime giuridico della cosa principale, pur potendo formare oggetto di rapporti autonomi. Nella vendita le pertinenze seguono il bene salvo diversa volonta. Il terzo proprietario puo rivendicarle ai sensi dell'art. 819 c.c. Il possesso della cosa principale si estende alla pertinenza; il rapporto termina con il venir meno della destinazione, il perimento o l'inidoneita dell'accessorio."; };
            openButton.Click += delegate { try { ChatGptBridge.OpenDedicatedConversation(); statusLabel.Text = "Chat dedicata aperta."; } catch (Exception ex) { ShowError(ex); } };
            prepareButton.Click += delegate
            {
                if (string.IsNullOrWhiteSpace(sourceBox.Text)) { statusLabel.Text = "Inserisci prima un testo."; return; }
                try { string prompt = ChatGptBridge.BuildPrompt(sourceBox.Text, intensityTrack.Value, objectsBox.Text, emotionsBox.Text); Clipboard.SetText(prompt); ChatGptBridge.OpenDedicatedConversation(); statusLabel.Text = "Prompt copiato. Nella chat: CTRL+V, INVIO. Poi copia il JSON e torna qui."; outputBox.Text = "PROMPT COPIATO NEGLI APPUNTI.\r\n\r\nChatGPT deve creare prima lo SCHEMA A CASCATA.\r\nL'audio sara solo un ripasso breve della struttura."; } catch (Exception ex) { ShowError(ex); }
            };
            importButton.Click += delegate
            {
                try { string raw = Clipboard.ContainsText() ? Clipboard.GetText() : string.Empty; currentPlan = ChatGptBridge.ParsePlan(raw); outputBox.Text = FormatPlan(currentPlan); statusLabel.Text = "Schema importato. Ora puoi ripassarlo o avviare l'audio breve."; } catch (Exception ex) { ShowError(ex); }
            };
            showPlanButton.Click += delegate { if (currentPlan == null) { statusLabel.Text = "Importa prima una risposta da ChatGPT."; return; } outputBox.Text = FormatPlan(currentPlan); };
            recallButton.Click += delegate
            {
                if (currentPlan == null) { statusLabel.Text = "Importa prima una risposta da ChatGPT."; return; }
                StringBuilder sb = new StringBuilder(); sb.AppendLine("ACTIVE RECALL"); sb.AppendLine(); int i = 1; foreach (string question in currentPlan.recall_questions) { sb.AppendLine(i + ". " + question); sb.AppendLine(); i++; } outputBox.Text = sb.ToString(); statusLabel.Text = "Rispondi ricostruendo lo schema a cascata senza guardarlo.";
            };
            speakButton.Click += delegate
            {
                if (currentPlan == null) { statusLabel.Text = "Importa prima una risposta da ChatGPT."; return; }
                try { speaker.SpeakPlanAsync(currentPlan.guided_movie, CurrentVoiceSettings()); statusLabel.Text = "Audio breve avviato. Chiudi gli occhi e ricostruisci la cascata."; } catch (Exception ex) { ShowError(ex); }
            };
            stopButton.Click += delegate { speaker.Stop(); statusLabel.Text = "Voce fermata."; };
            FormClosed += delegate { speaker.Stop(); };
        }

        private void ShowError(Exception ex)
        {
            statusLabel.Text = "ERRORE"; outputBox.Text = ex.Message; MessageBox.Show(ex.Message, "Memory Director", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }

        internal static string FormatPlan(MemoryPlan plan)
        {
            StringBuilder sb = new StringBuilder(); sb.AppendLine(plan.title.ToUpperInvariant()); sb.AppendLine(); sb.AppendLine("DOMANDA CHIAVE"); sb.AppendLine(plan.key_question); sb.AppendLine("    |"); sb.AppendLine("    v"); sb.AppendLine(); sb.AppendLine("CONCETTO CENTRALE"); sb.AppendLine(plan.core_concept); sb.AppendLine(); sb.AppendLine("SCHEMA A CASCATA");
            for (int i = 0; i < plan.cascade_branches.Count; i++)
            {
                CascadeBranch branch = plan.cascade_branches[i]; sb.AppendLine(); sb.AppendLine((i + 1) + ") " + branch.branch); if (branch.details != null) foreach (string detail in branch.details) sb.AppendLine("    -> " + detail); if (!string.IsNullOrWhiteSpace(branch.example)) sb.AppendLine("    es. " + branch.example);
            }
            if (plan.mnemonic_anchors != null && plan.mnemonic_anchors.Count > 0)
            {
                sb.AppendLine(); sb.AppendLine("GANCI MNEMONICI - SOLO PUNTI DIFFICILI"); foreach (MnemonicAnchor anchor in plan.mnemonic_anchors) sb.AppendLine("    * " + anchor.concept + " -> " + anchor.image);
            }
            sb.AppendLine(); sb.AppendLine("FOTOGRAMMA FINALE"); sb.AppendLine(plan.final_freeze_frame); sb.AppendLine(); sb.AppendLine("ACTIVE RECALL"); for (int i = 0; i < plan.recall_questions.Count; i++) sb.AppendLine((i + 1) + ". " + plan.recall_questions[i]); return sb.ToString();
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
            failures += Test("Prompt uses cascade schema", prompt.IndexOf("SCHEMA A CASCATA", StringComparison.OrdinalIgnoreCase) >= 0);
            failures += Test("Prompt limits audio duration", prompt.IndexOf("60-90 secondi", StringComparison.Ordinal) >= 0);
            failures += Test("Prompt requires JSON", prompt.IndexOf("SOLO con JSON valido", StringComparison.Ordinal) >= 0);
            string fenced = "```json\n{\"title\":\"Pertinenze\",\"key_question\":\"Qual e il regime delle pertinenze?\",\"core_concept\":\"La pertinenza segue normalmente la cosa principale.\",\"cascade_branches\":[{\"branch\":\"Regola\",\"details\":[\"art. 818 -> stesso regime\"],\"example\":\"vendita\"},{\"branch\":\"Autonomia\",\"details\":[\"rapporti autonomi possibili\"],\"example\":\"\"}],\"mnemonic_anchors\":[{\"concept\":\"818\",\"image\":\"un cappotto enorme avvolge casa e garage\"}],\"guided_movie\":[\"Chiudi gli occhi. Immagina...\",\"[pausa]\",\"Una casa al centro con pochi rami.\"],\"final_freeze_frame\":\"Casa al centro e rami ordinati.\",\"recall_questions\":[\"Qual e la regola?\",\"Quali sono i rami?\",\"Qual e l'eccezione?\",\"Quale articolo ricordi?\"]}\n```";
            try
            {
                MemoryPlan plan = ChatGptBridge.ParsePlan(fenced); failures += Test("Parse cascade JSON", plan != null && plan.title == "Pertinenze" && plan.cascade_branches.Count == 2 && plan.guided_movie.Count == 3); string formatted = MainForm.FormatPlan(plan); failures += Test("Formatted plan shows cascade", formatted.IndexOf("SCHEMA A CASCATA", StringComparison.Ordinal) >= 0);
            }
            catch (Exception ex) { Console.WriteLine("FAIL Parse cascade JSON: " + ex.Message); failures++; }
            failures += Test("Voice rate clamp", VoiceSettings.ClampRate(-99) == -10 && VoiceSettings.ClampRate(99) == 10);
            failures += Test("Pause clamp", VoiceSettings.ClampPause(10) == 300 && VoiceSettings.ClampPause(9999) == 4000);
            Console.WriteLine(failures == 0 ? "ALL SELF-TESTS PASSED" : (failures + " SELF-TESTS FAILED")); return failures == 0 ? 0 : 1;
        }

        private static int Test(string name, bool ok)
        {
            Console.WriteLine((ok ? "PASS " : "FAIL ") + name); return ok ? 0 : 1;
        }
    }
}
