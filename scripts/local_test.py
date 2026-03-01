import sys
sys.path.insert(0, '.')
from api.server import load_resources

def main():
    print('Loading resources...')
    meta, nn, embs, model = load_resources()
    print('Loaded:', len(meta), 'items; embeddings shape=', embs.shape)
    q = 'Hiring Java developer with teamwork and communication skills'
    vec = model.encode([q])[0]
    print('Encoded query vector length:', len(vec))
    dists, ids = nn.kneighbors([vec], n_neighbors=min(20, embs.shape[0]))
    print('Neighbors found:', len(ids[0]))
    print('\nTop 5:')
    for dist, idx in zip(dists[0][:5], ids[0][:5]):
        m = meta[int(idx)]
        print('-', (m.get('title') or '')[:80], m.get('url'), 'score', 1-float(dist))

if __name__ == '__main__':
    main()
