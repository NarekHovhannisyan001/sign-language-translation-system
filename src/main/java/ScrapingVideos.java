import kong.unirest.HttpResponse;
import kong.unirest.Unirest;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

public class ScrapingVideos {
    public static void main(String[] args) {
        new ScrapingVideos().foo();
    }

    void foo() {
        Unirest.config().reset()
                .followRedirects(true)
                .enableCookieManagement(false);

        HttpResponse<String> response = Unirest.get("https://hy.wiktionary.org/wiki/%D5%80%D5%A1%D5%B5%D5%A5%D6%80%D5%A5%D5%B6_%D5%AA%D5%A5%D5%BD%D5%BF%D5%A5%D6%80%D5%AB_%D5%AC%D5%A5%D5%A6%D5%BE%D5%AB_%D5%A2%D5%A1%D5%BC%D5%A1%D6%80%D5%A1%D5%B6")
                .header("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7")
                .header("accept-language", "en-US,en;q=0.9,ru;q=0.8,hy;q=0.7")
                .header("cache-control", "max-age=0")
                .header("priority", "u=0, i")
                .header("sec-ch-ua", "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"")
                .header("sec-ch-ua-mobile", "?0")
                .header("sec-ch-ua-platform", "\"Linux\"")
                .header("sec-fetch-dest", "document")
                .header("sec-fetch-mode", "navigate")
                .header("sec-fetch-site", "cross-site")
                .header("sec-fetch-user", "?1")
                .header("upgrade-insecure-requests", "1")
                .header("user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")
                .header("Cookie", "WMF-Last-Access=04-Jul-2025; WMF-Last-Access-Global=04-Jul-2025; GeoIP=AM:ER:Yerevan:40.18:44.51:v4; WMF-Uniq=aICSP6511KIeaKKlAO-BPQImAAEBAFvdEEvuYTBHoK5dfsirRQUI8ZRC47sgsXyL; hywiktionarymwuser-sessionId=3e9c505b4c59aa0acca0; NetworkProbeLimit=0.001")
                .asString();

        Elements bigDiv = Jsoup.parse(response.getBody()).select("#mwBQ > section");


        for (int i = 6; i < bigDiv.size(); i++) {
            Elements ul = bigDiv.get(i).select("ul");
            oneSectionHandling(ul);
        }
//        Elements select = Jsoup.parse(response.getBody()).select("#mwBw > ul");
//        oneSectionHandling(select);

    }

    private void oneSectionHandling(Elements select) {
        for (Element element : select) {
            Elements elementsByTag = element.getElementsByTag("li");

            for (Element element1 : elementsByTag) {
                String attr = element1.select("a").attr("href");
                String videoUrl = scrapeHtml("https:" + attr);
                String videoName = element1.select("a").text();
                if (videoUrl != null) {
                    downloadVideo(videoUrl, videoName);
                } else {
                    System.out.println("No video URL found, cannot download.");
                }
            }

        }
    }

    int OUTPUT_FILE = 0;

    private String scrapeHtml(String pageUrl) {
        String videoUrl = null;
        try {
            Document doc = Jsoup.connect(pageUrl)
                    .userAgent("VideoDownloaderBot/1.0 (contact: levsyan22@gmail.com)")
                    .timeout(10000)
                    .get();

            Element videoLink = doc.selectFirst("div.fullMedia a.internal");
            if (videoLink != null) {
                videoUrl = videoLink.attr("href");
                if (videoUrl.startsWith("//")) {
                    videoUrl = "https:" + videoUrl;
                }
                System.out.println("Video URL: " + videoUrl);
            } else {
                System.out.println("Video URL not found.");
            }


            Element fileSizeElement = doc.selectFirst("#P3575 .wbmi-entity-label");
            if (fileSizeElement != null) {
                System.out.println("File Size: " + fileSizeElement.text());
            } else {
                System.out.println("File Size not found.");
            }

            Element heightElement = doc.selectFirst("#P2048 .wbmi-entity-label");
            Element widthElement = doc.selectFirst("#P2049 .wbmi-entity-label");
            if (heightElement != null && widthElement != null) {
                System.out.println("Resolution: " + widthElement.text() + " × " + heightElement.text());
            } else {
                System.out.println("Resolution not found.");
            }

            Element durationElement = doc.selectFirst("#P2047 .wbmi-entity-label");
            if (durationElement != null) {
                System.out.println("Duration: " + durationElement.text());
            } else {
                System.out.println("Duration not found.");
            }

        } catch (Exception e) {
            System.err.println("Error fetching or parsing HTML: " + e.getMessage());
        }
        return videoUrl;
    }

    /**
     * Downloads the video from the specified URL.
     *
     * @param videoUrl The URL of the video to download.
     */
    private void downloadVideo(String videoUrl, String videoName) {
    try {
    
        Path videosDir = Path.of("videos");
        if (!Files.exists(videosDir)) {
            Files.createDirectories(videosDir);
        }
        
        String extension = "";
        if (videoUrl.contains(".")) {
            String urlPath = videoUrl.split("\\?")[0];
            extension = urlPath.substring(urlPath.lastIndexOf("."));
            if (extension.length() > 5) {
                extension = ".webm";
            }
        } else {
            extension = ".webm";
        }
        
        if (!videoName.contains(".")) {
            videoName = videoName + extension;
        }
        
        videoName = videoName.replaceAll("[/\\\\:*?\"<>|]", "_");
        
        URL url = new URL(videoUrl);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestProperty("User-Agent", "VideoDownloaderBot/1.0 (contact: levsyan22@gmail.com)");

        int responseCode = connection.getResponseCode();
        System.out.println("Response code for " + videoName + ": " + responseCode);
        
        if (responseCode == HttpURLConnection.HTTP_OK) {
            String contentType = connection.getContentType();
            System.out.println("Content-Type: " + contentType);
            
            OUTPUT_FILE++;
            Path outputPath = videosDir.resolve(videoName);
            
            long totalBytes = 0;
            try (InputStream inputStream = connection.getInputStream();
                 FileOutputStream outputStream = new FileOutputStream(outputPath.toFile())) {
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = inputStream.read(buffer)) != -1) {
                    outputStream.write(buffer, 0, bytesRead);
                    totalBytes += bytesRead;
                }
                System.out.println("✓ Video downloaded: " + outputPath + " (" + formatBytes(totalBytes) + ")");
            }
        } else {
            System.err.println("✗ Failed: " + videoName + " (HTTP " + responseCode + ")");
            Files.writeString(Path.of("FailedUrl.txt"), 
                videoName + " | " + videoUrl + " | HTTP " + responseCode + "\n", 
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        }
    } catch (Exception e) {
        System.err.println("Error downloading '" + videoName + "': " + e.getMessage());
        try {
            Files.writeString(Path.of("FailedUrl.txt"), 
                videoName + " | " + videoUrl + " | Error: " + e.getMessage() + "\n", 
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (Exception ex) {
            // Ignore
        }
    }
}

private String formatBytes(long bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return String.format("%.2f KB", bytes / 1024.0);
    return String.format("%.2f MB", bytes / (1024.0 * 1024.0));
}
}
