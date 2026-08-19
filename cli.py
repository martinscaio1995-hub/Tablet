import argparse

from src.agents.idea_agent import generate_ideas
from src.agents.trends_agent import research_trends
from src.config import config
from src.orchestrator import run_pipeline


def cmd_ideas(args):
    for idea in generate_ideas(args.niche or config.content_niche, count=args.count):
        print(f"- {idea}")


def cmd_trends(args):
    for trend in research_trends(args.niche or config.content_niche, count=args.count):
        print(f"\n- {trend['topic']}")
        print(f"  por quê: {trend['why_now']}")
        print(f"  ângulo:  {trend['angle']}")
        if trend["product_tie_in"]:
            print(f"  produto: {trend['product_tie_in']}")


def cmd_run(args):
    result = run_pipeline(
        niche=args.niche, idea=args.idea, post=args.post, use_trends=not args.no_trends
    )
    print(f"\nIdeia: {result['idea']}")
    print(f"Caption: {result['script'].caption}")
    if result["script"].cta:
        print(f"CTA: {result['script'].cta}")
    print(f"Hashtags: {', '.join(result['script'].hashtags)}")
    print(f"Video salvo em: {result['video_path']}")
    if args.post:
        print(f"Postado: {result['posted']}")
        print(f"Status: {result['publish_status']}")
    else:
        print("\n(video gerado localmente; use --post para publicar no TikTok)")


def cmd_auth(_args):
    from src.tiktok import auth

    auth._run_local_flow()


def main():
    parser = argparse.ArgumentParser(description="Pipeline de agentes para conteudo do TikTok")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ideas = sub.add_parser("ideas", help="Gerar ideias de video")
    p_ideas.add_argument("--niche", default=None)
    p_ideas.add_argument("--count", type=int, default=5)
    p_ideas.set_defaults(func=cmd_ideas)

    p_trends = sub.add_parser(
        "trends", help="Pesquisar o que esta em alta no nicho (busca na web)"
    )
    p_trends.add_argument("--niche", default=None)
    p_trends.add_argument("--count", type=int, default=5)
    p_trends.set_defaults(func=cmd_trends)

    p_run = sub.add_parser("run", help="Gerar (e opcionalmente postar) um video")
    p_run.add_argument("--niche", default=None)
    p_run.add_argument("--idea", default=None, help="Pular geracao de ideia e usar esta")
    p_run.add_argument("--post", action="store_true", help="Publicar no TikTok apos gerar")
    p_run.add_argument(
        "--no-trends",
        action="store_true",
        help="Nao pesquisar tendencias antes de gerar a ideia (mais rapido e barato)",
    )
    p_run.set_defaults(func=cmd_run)

    p_auth = sub.add_parser("auth", help="Autorizar o app no TikTok (OAuth)")
    p_auth.set_defaults(func=cmd_auth)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
