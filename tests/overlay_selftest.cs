using System;
using System.Drawing;
using System.IO;
using PocketWorldQuickAssembly;

namespace PocketWorldQuickAssemblyTests
{
    internal static class Program
    {
        private static int Main(string[] args)
        {
            if (args.Length != 1)
                return 100;
            string root = Path.GetFullPath(args[0]);
            string templatePath = Path.Combine(
                root,
                "assets",
                "hint_windmill.png");
            using (Bitmap template = new Bitmap(templatePath))
            using (Bitmap canvas = new Bitmap(900, 1600))
            using (Graphics graphics = Graphics.FromImage(canvas))
            using (SolidBrush background = new SolidBrush(Color.FromArgb(247, 242, 235)))
            {
                graphics.FillRectangle(background, 0, 0, canvas.Width, canvas.Height);
                graphics.DrawImage(template, 804, 190);
                TemplateMatch match = OverlayForm.MatchTemplate(canvas, templatePath);
                if (match == null || match.Score < 0.65)
                    return 1;
                if (
                    Math.Abs(match.CenterX - (804 + template.Width / 2)) > 2 ||
                    Math.Abs(match.CenterY - (190 + template.Height / 2)) > 2)
                    return 2;
            }

            using (Bitmap blank = new Bitmap(900, 1600))
            using (Graphics graphics = Graphics.FromImage(blank))
            using (SolidBrush background = new SolidBrush(Color.FromArgb(247, 242, 235)))
            {
                graphics.FillRectangle(background, 0, 0, blank.Width, blank.Height);
                TemplateMatch match = OverlayForm.MatchTemplate(blank, templatePath);
                if (match != null && match.Score >= 0.65)
                    return 3;
            }
            return 0;
        }
    }
}
