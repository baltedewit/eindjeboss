import discord
import logging
import textwrap
from discord import app_commands
from discord.ext import commands
from wikipedia_summary import WikipediaSummary


class Wiki(commands.Cog):

    wiki_summary: WikipediaSummary

    def __init__(self, client):
        self.client = client
        self.wiki_summary = WikipediaSummary()

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f"[{__name__}] Cog is ready")

    @app_commands.command(name="wiki", description="Search for a page on Wikipedia.")
    async def wiki(self, interaction: discord.Interaction, query: str):
        details = self.wiki_summary.get_summary(query)
        if not details:
            await interaction.response.send_message(f"Could not find page for query: {query}", ephemeral=True)
            return
        try:
            await interaction.response.send_message(embed=self.get_embed_from_wiki_page(details), view=WikiView(details.url))
            logging.info(f"Sent Wiki page to {interaction.user.name} for query {query}")
            return
        except Exception as e:
            logging.info(f"Failed to send Wiki page to {interaction.user.name} for query {query}")
            logging.error(e)

    def get_embed_from_wiki_page(self, page_details):
        embed = discord.Embed(title=page_details.title, url=page_details.url, color=discord.Color.teal())
        if page_details.description:
            embed.add_field(name="Description", value=page_details.description, inline=True)
        embed.add_field(name="Summary", value=textwrap.shorten(page_details.summary, width=1024), inline=False)
        embed.set_image(url=page_details.thumbnail_url)
        return embed

class WikiView(discord.ui.View):
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.add_item(discord.ui.Button(label="Wikipedia", url=self.url, style=discord.ButtonStyle.url))

async def setup(bot):
    await bot.add_cog(Wiki(bot))
