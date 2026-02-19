using System;
using System.Net.Http;
using System.Collections.Generic;
using System.Text.Json;
using System.Text;

public static class FRCONSOLE
{
    public static JsonElement response;

    private static readonly string apiUrl = "https://frconsole.onrender.com/client_login";
    private static readonly string messageUrl = "https://frconsole.onrender.com/get_messages";
    private static readonly string category = "FRCONSOLE";

    private static string GetHWID()
    {
        return Environment.MachineName; // Simple HWID logic
    }

    public static void login(string username, string password)
    {
        using (var client = new HttpClient())
        {
            var values = new Dictionary<string, string>
            {
                { "category", category },
                { "username", username },
                { "password", password },
                { "hwid", GetHWID() }
            };

            var content = new FormUrlEncodedContent(values);
            try
            {
                var responseMessage = client.PostAsync(apiUrl, content).Result;
                string resultString = responseMessage.Content.ReadAsStringAsync().Result;

                response = JsonSerializer.Deserialize<JsonElement>(resultString);
            }
            catch (Exception ex)
            {
                string err = "{\"status\":\"error\",\"message\":\"Connection error: " + ex.Message + "\"}";
                response = JsonSerializer.Deserialize<JsonElement>(err);
            }
        }
    }

    public static string GetLatestMessage(string username)
    {
        using (var client = new HttpClient())
        {
            var values = new Dictionary<string, string>
        {
            { "category", category },
            { "username", username }
        };

            var content = new FormUrlEncodedContent(values);

            try
            {
                var res = client.PostAsync(messageUrl, content).Result;
                var resString = res.Content.ReadAsStringAsync().Result;
                var msgData = JsonSerializer.Deserialize<JsonElement>(resString);

                if (msgData.GetProperty("status").GetString() == "success" &&
                    msgData.TryGetProperty("messages", out JsonElement list) &&
                    list.GetArrayLength() > 0)
                {
                    var last = list[list.GetArrayLength() - 1];
                    return $"📩 {last.GetProperty("time").GetString()}\n\n{last.GetProperty("text").GetString()}";
                }
            }
            catch (Exception ex)
            {
                return "❌ Failed to load message: " + ex.Message;
            }
        }

        return null;

    }
}
