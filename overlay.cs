using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace PocketWorldQuickAssembly
{
    internal sealed class AdbResult
    {
        public int ExitCode;
        public string StdOut;
        public string StdErr;
    }

    internal sealed class AutoCheckResult
    {
        public bool Success;
        public string Message;
    }

    internal sealed class TemplateMatch
    {
        public double Score;
        public int Left;
        public int Top;
        public int Width;
        public int Height;
        public int CenterX { get { return Left + Width / 2; } }
        public int CenterY { get { return Top + Height / 2; } }
    }

    internal sealed class OverlayForm : Form
    {
        private const string PackageName = "com.puzzle.miniworld.cn";
        private const string DeviceId = "127.0.0.1:16416";
        private const double MatchThreshold = 0.65;
        private const int ExpandedWidth = 292;
        private const int ExpandedHeight = 238;
        private const int MinimizedSize = 72;

        private readonly string adbPath;
        private readonly string[] templatePaths;
        private readonly Font titleFont = new Font("Microsoft YaHei UI", 11f, FontStyle.Bold);
        private readonly Font subtitleFont = new Font("Microsoft YaHei UI", 8.5f);
        private readonly Font autoFont = new Font("Microsoft YaHei UI", 15f, FontStyle.Bold);
        private readonly Font circleFont = new Font("Microsoft YaHei UI", 20f, FontStyle.Bold);
        private readonly Font iconFont = new Font("Microsoft YaHei UI", 12f, FontStyle.Bold);
        private readonly Timer gameTimer;

        private bool expanded = true;
        private bool busy;
        private bool allowClose;
        private bool dragging;
        private bool dragMoved;
        private int gameMisses;
        private Point dragStart;
        private Point windowStart;
        private string statusText = "等待游戏";
        private Color statusColor = Color.FromArgb(159, 179, 191);

        public OverlayForm()
        {
            string rootDirectory = AppDomain.CurrentDomain.BaseDirectory;
            adbPath = Path.Combine(
                Environment.GetEnvironmentVariable("MUMU_ROOT") ??
                    @"D:\TapTap\Support\android_emulator",
                "engine",
                "nx_main",
                "adb.exe");
            templatePaths = new string[]
            {
                Path.Combine(rootDirectory, "assets", "hint_windmill.png"),
                Path.Combine(rootDirectory, "assets", "hint_kyoto.png")
            };

            Text = "我爱拼模型快速拼装助手";
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.Manual;
            TopMost = true;
            ShowInTaskbar = false;
            BackColor = Color.FromArgb(23, 34, 45);
            DoubleBuffered = true;
            SetStyle(
                ControlStyles.AllPaintingInWmPaint |
                ControlStyles.OptimizedDoubleBuffer |
                ControlStyles.UserPaint,
                true);

            Rectangle area = Screen.PrimaryScreen.WorkingArea;
            Location = new Point(area.Right - ExpandedWidth - 48, area.Top + 120);
            Size = new Size(ExpandedWidth, ExpandedHeight);
            UpdateWindowRegion();

            gameTimer = new Timer();
            gameTimer.Interval = 2500;
            gameTimer.Tick += delegate { CheckGameState(); };
            gameTimer.Start();
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            SetStatus("等待拼装页", Color.FromArgb(159, 179, 191));
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (!allowClose && e.CloseReason == CloseReason.UserClosing)
            {
                DialogResult answer = MessageBox.Show(
                    this,
                    "是否关闭插件功能？",
                    "退出插件",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);
                if (answer != DialogResult.Yes)
                {
                    e.Cancel = true;
                    return;
                }
            }
            allowClose = true;
            gameTimer.Stop();
            base.OnFormClosing(e);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            Graphics graphics = e.Graphics;
            graphics.SmoothingMode = SmoothingMode.AntiAlias;
            if (!expanded)
            {
                DrawMinimized(graphics);
                return;
            }

            using (SolidBrush background = new SolidBrush(Color.FromArgb(23, 34, 45)))
            using (Pen border = new Pen(Color.FromArgb(43, 70, 87)))
            using (GraphicsPath path = RoundedRectangle(
                new Rectangle(1, 1, Width - 3, Height - 3),
                18))
            {
                graphics.FillPath(background, path);
                graphics.DrawPath(border, path);
            }

            DrawText(graphics, "我爱拼模型", titleFont, Color.FromArgb(241, 245, 247), 20, 16);
            DrawText(graphics, "快速拼装助手", subtitleFont, Color.FromArgb(143, 169, 184), 20, 43);
            DrawCircleButton(graphics, MinusRect, "−", Color.FromArgb(35, 53, 66));
            DrawCircleButton(graphics, CloseRect, "×", Color.FromArgb(181, 72, 72));
            DrawAutoButton(graphics);
            DrawText(graphics, statusText, subtitleFont, statusColor, 20, 166);
            using (Font footerFont = new Font("Microsoft YaHei UI", 7.5f))
            {
                DrawText(
                    graphics,
                    "仅调用游戏原生自动拼接 · 不扣道具",
                    footerFont,
                    Color.FromArgb(111, 135, 149),
                    20,
                    195);
            }
        }

        private void DrawMinimized(Graphics graphics)
        {
            using (SolidBrush fill = new SolidBrush(Color.FromArgb(15, 118, 110)))
            using (Pen outline = new Pen(Color.FromArgb(45, 212, 191), 2))
            {
                graphics.FillEllipse(fill, 3, 3, Width - 7, Height - 7);
                graphics.DrawEllipse(outline, 3, 3, Width - 7, Height - 7);
            }
            DrawCenteredText(graphics, "拼", circleFont, Color.White, ClientRectangle);
        }

        private void DrawAutoButton(Graphics graphics)
        {
            using (GraphicsPath path = RoundedRectangle(AutoRect, 14))
            using (SolidBrush fill = new SolidBrush(
                busy ? Color.FromArgb(49, 81, 90) : Color.FromArgb(15, 118, 110)))
            using (Pen outline = new Pen(
                busy ? Color.FromArgb(69, 99, 113) : Color.FromArgb(45, 212, 191)))
            {
                graphics.FillPath(fill, path);
                graphics.DrawPath(outline, path);
            }
            DrawCenteredText(
                graphics,
                busy ? "检测中..." : "自动拼完",
                autoFont,
                Color.White,
                AutoRect);
        }

        private void DrawCircleButton(
            Graphics graphics,
            Rectangle rectangle,
            string text,
            Color fill)
        {
            using (SolidBrush brush = new SolidBrush(fill))
            {
                graphics.FillEllipse(brush, rectangle);
            }
            DrawCenteredText(graphics, text, iconFont, Color.White, rectangle);
        }

        private void DrawText(
            Graphics graphics,
            string text,
            Font font,
            Color color,
            int x,
            int y)
        {
            using (SolidBrush brush = new SolidBrush(color))
            {
                graphics.DrawString(text, font, brush, x, y);
            }
        }

        private void DrawCenteredText(
            Graphics graphics,
            string text,
            Font font,
            Color color,
            Rectangle rectangle)
        {
            TextFormatFlags flags =
                TextFormatFlags.HorizontalCenter |
                TextFormatFlags.VerticalCenter |
                TextFormatFlags.SingleLine |
                TextFormatFlags.NoPadding;
            TextRenderer.DrawText(
                graphics,
                text,
                font,
                rectangle,
                color,
                Color.Transparent,
                flags);
        }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            base.OnMouseDown(e);
            if (e.Button != MouseButtons.Left)
                return;
            dragging = true;
            dragMoved = false;
            dragStart = Cursor.Position;
            windowStart = Location;
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            if (!dragging)
                return;
            Point current = Cursor.Position;
            int dx = current.X - dragStart.X;
            int dy = current.Y - dragStart.Y;
            if (Math.Abs(dx) + Math.Abs(dy) > 4)
                dragMoved = true;
            Location = new Point(windowStart.X + dx, windowStart.Y + dy);
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            if (!dragging)
                return;
            dragging = false;
            if (!dragMoved)
                HandleClick(e.Location);
        }

        private void HandleClick(Point point)
        {
            if (!expanded)
            {
                Expand();
                return;
            }
            if (MinusRect.Contains(point))
            {
                MinimizeToCircle();
                return;
            }
            if (CloseRect.Contains(point))
            {
                Close();
                return;
            }
            if (AutoRect.Contains(point))
            {
                StartAutoFinish();
            }
        }

        private void StartAutoFinish()
        {
            if (busy)
                return;
            busy = true;
            SetStatus("检测拼装页面...", Color.FromArgb(216, 228, 232));
            Invalidate();
            Task.Run(() =>
            {
                AutoCheckResult result = TryAutoFinish();
                BeginInvoke(new Action(() => FinishAutoAttempt(result)));
            });
        }

        private AutoCheckResult TryAutoFinish()
        {
            if (!File.Exists(adbPath))
                return Fail("ADB 路径无效");

            AdbResult pid = RunAdb(new string[] { "shell", "pidof", PackageName }, 3000);
            if (pid == null || pid.ExitCode != 0 || string.IsNullOrWhiteSpace(pid.StdOut))
                return Fail("游戏未运行");

            AdbResult activity = RunAdb(
                new string[] { "shell", "dumpsys", "activity", "activities" },
                4000);
            if (activity == null || !activity.StdOut.Contains(PackageName + "/"))
                return Fail("游戏不在前台");

            Bitmap screenshot = CaptureScreenshot();
            if (screenshot == null)
                return Fail("无法读取游戏画面");
            try
            {
                TemplateMatch best = null;
                foreach (string templatePath in templatePaths)
                {
                    if (!File.Exists(templatePath))
                        continue;
                    TemplateMatch candidate = MatchTemplate(screenshot, templatePath);
                    if (candidate == null)
                        continue;
                    if (best == null || candidate.Score > best.Score)
                        best = candidate;
                }
                if (best == null || best.Score < MatchThreshold)
                    return Fail("请先进入拼装页");

                AdbResult tap = RunAdb(
                    new string[]
                    {
                        "shell",
                        "input",
                        "tap",
                        best.CenterX.ToString(),
                        best.CenterY.ToString()
                    },
                    3000);
                if (tap == null || tap.ExitCode != 0)
                    return Fail("点击发送失败");
                return new AutoCheckResult
                {
                    Success = true,
                    Message = "已触发自动拼完"
                };
            }
            finally
            {
                screenshot.Dispose();
            }
        }

        private AutoCheckResult Fail(string message)
        {
            return new AutoCheckResult
            {
                Success = false,
                Message = message
            };
        }

        private void FinishAutoAttempt(AutoCheckResult result)
        {
            busy = false;
            SetStatus(
                result.Message,
                result.Success
                    ? Color.FromArgb(125, 211, 199)
                    : Color.FromArgb(240, 181, 108));
            Invalidate();
            Task.Delay(result.Success ? 1300 : 900).ContinueWith(
                delegate
                {
                    if (IsDisposed)
                        return;
                    BeginInvoke(new Action(delegate
                    {
                        if (!busy)
                            SetStatus("等待拼装页", Color.FromArgb(159, 179, 191));
                    }));
                });
        }

        private void CheckGameState()
        {
            Task.Run(() =>
            {
                AdbResult result = RunAdb(
                    new string[] { "shell", "pidof", PackageName },
                    2000);
                bool running =
                    result != null &&
                    result.ExitCode == 0 &&
                    !string.IsNullOrWhiteSpace(result.StdOut);
                BeginInvoke(new Action(delegate
                {
                    if (IsDisposed)
                        return;
                    if (running)
                    {
                        gameMisses = 0;
                    }
                    else
                    {
                        gameMisses++;
                        if (gameMisses >= 2 && expanded)
                            MinimizeToCircle();
                    }
                }));
            });
        }

        private void SetStatus(string text, Color color)
        {
            statusText = text;
            statusColor = color;
            if (expanded)
                Invalidate();
        }

        private void MinimizeToCircle()
        {
            if (busy)
                return;
            Point location = Location;
            expanded = false;
            Size = new Size(MinimizedSize, MinimizedSize);
            Location = location;
            UpdateWindowRegion();
            Invalidate();
        }

        private void Expand()
        {
            Point location = Location;
            expanded = true;
            Size = new Size(ExpandedWidth, ExpandedHeight);
            Location = location;
            UpdateWindowRegion();
            Invalidate();
        }

        private void UpdateWindowRegion()
        {
            if (expanded)
            {
                Region = new Region(RoundedRectangle(
                    new Rectangle(0, 0, Width, Height),
                    18));
            }
            else
            {
                using (GraphicsPath ellipse = new GraphicsPath())
                {
                    ellipse.AddEllipse(0, 0, Width - 1, Height - 1);
                    Region = new Region(ellipse);
                }
            }
        }

        private Rectangle AutoRect
        {
            get { return new Rectangle(16, 80, Width - 32, 68); }
        }

        private Rectangle MinusRect
        {
            get { return new Rectangle(Width - 62, 16, 24, 24); }
        }

        private Rectangle CloseRect
        {
            get { return new Rectangle(Width - 32, 16, 24, 24); }
        }

        private static GraphicsPath RoundedRectangle(Rectangle rectangle, int radius)
        {
            int diameter = radius * 2;
            GraphicsPath path = new GraphicsPath();
            path.AddArc(rectangle.X, rectangle.Y, diameter, diameter, 180, 90);
            path.AddArc(
                rectangle.Right - diameter,
                rectangle.Y,
                diameter,
                diameter,
                270,
                90);
            path.AddArc(
                rectangle.Right - diameter,
                rectangle.Bottom - diameter,
                diameter,
                diameter,
                0,
                90);
            path.AddArc(
                rectangle.X,
                rectangle.Bottom - diameter,
                diameter,
                diameter,
                90,
                90);
            path.CloseFigure();
            return path;
        }

        private Bitmap CaptureScreenshot()
        {
            try
            {
                ProcessStartInfo startInfo = new ProcessStartInfo();
                startInfo.FileName = adbPath;
                startInfo.Arguments = string.Format(
                    "-s {0} exec-out screencap -p",
                    DeviceId);
                startInfo.UseShellExecute = false;
                startInfo.CreateNoWindow = true;
                startInfo.RedirectStandardOutput = true;
                startInfo.RedirectStandardError = true;
                using (Process process = Process.Start(startInfo))
                {
                    if (process == null)
                        return null;
                    Task<string> errorTask = Task.Run(
                        () => process.StandardError.ReadToEnd());
                    using (MemoryStream stream = new MemoryStream())
                    {
                        process.StandardOutput.BaseStream.CopyTo(stream);
                        if (!process.WaitForExit(6000))
                        {
                            TryKill(process);
                            return null;
                        }
                        errorTask.Wait(1000);
                        if (process.ExitCode != 0 || stream.Length < 8)
                            return null;
                        stream.Position = 0;
                        return new Bitmap(stream);
                    }
                }
            }
            catch
            {
                return null;
            }
        }

        internal static TemplateMatch MatchTemplate(Bitmap image, string templatePath)
        {
            using (Bitmap template = new Bitmap(templatePath))
            {
                int templateWidth = template.Width;
                int templateHeight = template.Height;
                int count = templateWidth * templateHeight;
                double[] templateGray = new double[count];
                double templateMean = 0;
                for (int y = 0; y < templateHeight; y++)
                {
                    for (int x = 0; x < templateWidth; x++)
                    {
                        Color color = template.GetPixel(x, y);
                        double gray =
                            0.299 * color.R +
                            0.587 * color.G +
                            0.114 * color.B;
                        templateGray[y * templateWidth + x] = gray;
                        templateMean += gray;
                    }
                }
                templateMean /= count;
                double templateNorm = 0;
                for (int i = 0; i < count; i++)
                {
                    templateGray[i] -= templateMean;
                    templateNorm += templateGray[i] * templateGray[i];
                }
                if (templateNorm <= 0)
                    return null;

                int searchLeft = (int)(image.Width * 0.80);
                int searchTop = (int)(image.Height * 0.02);
                int searchRight = image.Width - templateWidth;
                int searchBottom = (int)(image.Height * 0.46) - templateHeight;
                TemplateMatch best = null;
                for (int y = searchTop; y <= searchBottom; y += 3)
                {
                    for (int x = searchLeft; x <= searchRight; x += 3)
                    {
                        double sum = 0;
                        double sumSquared = 0;
                        double dot = 0;
                        for (int ty = 0; ty < templateHeight; ty++)
                        {
                            for (int tx = 0; tx < templateWidth; tx++)
                            {
                                Color color = image.GetPixel(x + tx, y + ty);
                                double gray =
                                    0.299 * color.R +
                                    0.587 * color.G +
                                    0.114 * color.B;
                                sum += gray;
                                sumSquared += gray * gray;
                                dot += gray * templateGray[ty * templateWidth + tx];
                            }
                        }
                        double variance = sumSquared - sum * sum / count;
                        if (variance <= 0)
                            continue;
                        double score = dot / Math.Sqrt(variance * templateNorm);
                        if (best == null || score > best.Score)
                        {
                            best = new TemplateMatch
                            {
                                Score = score,
                                Left = x,
                                Top = y,
                                Width = templateWidth,
                                Height = templateHeight
                            };
                        }
                    }
                }
                return best;
            }
        }

        private AdbResult RunAdb(string[] arguments, int timeoutMilliseconds)
        {
            try
            {
                ProcessStartInfo startInfo = new ProcessStartInfo();
                startInfo.FileName = adbPath;
                startInfo.Arguments =
                    "-s " + DeviceId + " " + string.Join(" ", arguments);
                startInfo.UseShellExecute = false;
                startInfo.CreateNoWindow = true;
                startInfo.WindowStyle = ProcessWindowStyle.Hidden;
                startInfo.RedirectStandardOutput = true;
                startInfo.RedirectStandardError = true;
                using (Process process = Process.Start(startInfo))
                {
                    if (process == null)
                        return null;
                    Task<string> stdout = process.StandardOutput.ReadToEndAsync();
                    Task<string> stderr = process.StandardError.ReadToEndAsync();
                    if (!process.WaitForExit(timeoutMilliseconds))
                    {
                        TryKill(process);
                        return null;
                    }
                    return new AdbResult
                    {
                        ExitCode = process.ExitCode,
                        StdOut = stdout.Result,
                        StdErr = stderr.Result
                    };
                }
            }
            catch
            {
                return null;
            }
        }

        private static void TryKill(Process process)
        {
            try
            {
                process.Kill();
            }
            catch
            {
            }
        }
    }

    internal static class Program
    {
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        private static extern IntPtr CreateMutex(
            IntPtr attributes,
            bool initialOwner,
            string name);

        [DllImport("kernel32.dll")]
        private static extern uint GetLastError();

        [STAThread]
        private static void Main()
        {
            IntPtr mutex = CreateMutex(
                IntPtr.Zero,
                true,
                "Global\\PocketWorldQuickAssemblyOverlay");
            if (mutex == IntPtr.Zero || GetLastError() == 183)
                return;

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new OverlayForm());
        }
    }
}
