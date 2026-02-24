import sqlite3
import os
import hashlib
import numpy as np
import pandas as pd
                
abs_min = 1e-6 # absolute threshold
sc_min = 0.5 # 5% noise threshold
REQUIRED_INPUT_COLUMNS = {
        'Directed_Evolution_Generation',
        'DNA_Quantification_fg',
        'Protein_Quantification_pg',
        'Control',
        'Protein_Sequence'
}


def _existing_candidate_paths(relative_path):
        """
        Candidate absolute paths for a relative sqlite DB path.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cwd = os.getcwd()
        candidates = [
                os.path.join(cwd, relative_path),
                os.path.join(script_dir, relative_path),
                os.path.join(script_dir, 'Directed-Evolution-Portal', relative_path),
                os.path.join(cwd, 'Directed-Evolution-Portal', relative_path),
                os.path.join(cwd, 'Desktop', 'Directed-Evolution-Portal', relative_path),
                os.path.join(script_dir, '..', 'Directed-Evolution-Portal', relative_path),
        ]
        seen = set()
        ordered = []
        for p in [os.path.abspath(p) for p in candidates]:
                if p not in seen:
                        seen.add(p)
                        ordered.append(p)
        return ordered


def resolve_db_path_from_url(database_url):
        """
        Resolve a filesystem path from a SQLAlchemy DATABASE_URL.
        Currently supports sqlite URLs.
        """
        if not database_url:
                return None
        if not database_url.startswith('sqlite:///'):
                raise ValueError('Only sqlite:/// DATABASE_URL is supported by this script.')
        raw_path = database_url.replace('sqlite:///', '', 1)
        if os.path.isabs(raw_path):
                return raw_path
        for candidate in _existing_candidate_paths(raw_path):
                if os.path.exists(candidate):
                        return candidate
        # fallback to CWD-based absolute path
        return os.path.abspath(raw_path)


def list_tables(conn):
        q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        return pd.read_sql_query(q, conn)['name'].tolist()


def table_columns(conn, table_name):
        info = pd.read_sql_query(f'PRAGMA table_info("{table_name}")', conn)
        return set(info['name'].tolist())


def infer_input_table(conn):
        tables = list_tables(conn)
        for t in tables:
                cols = table_columns(conn, t)
                if REQUIRED_INPUT_COLUMNS.issubset(cols):
                        return t
        return None


def load_input_from_db(db_path, source_table=None, source_query=None):
        """
        Load activity input data from a SQLite database.
        Use either source_table or source_query.
        """
        if source_query and source_table:
                raise ValueError('Provide source_table or source_query, not both.')

        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        if not os.path.exists(db_path):
                raise FileNotFoundError(
                        f'Database file not found: {db_path}. '
                        'Set ACTIVITY_INPUT_DB_PATH to an existing DB file.'
                )

        with sqlite3.connect(db_path) as conn:
                tables = list_tables(conn)
                if source_query:
                        return pd.read_sql_query(source_query, conn)

                table_to_use = source_table
                if not table_to_use:
                        table_to_use = infer_input_table(conn)
                        if not table_to_use:
                                raise ValueError(
                                        'No input table specified and no table with required columns was found. '
                                        f'Required columns: {sorted(REQUIRED_INPUT_COLUMNS)}. '
                                        f'Available tables: {tables}'
                                )
                if table_to_use not in tables:
                        raise ValueError(
                                f'Input table "{table_to_use}" not found in {db_path}. '
                                f'Available tables: {tables}'
                        )

                df = pd.read_sql_query(f'SELECT * FROM "{table_to_use}"', conn)
                missing = REQUIRED_INPUT_COLUMNS - set(df.columns)
                if missing:
                        raise ValueError(
                                f'Table "{table_to_use}" is missing required columns: {sorted(missing)}'
                        )
                return df


# SQLite table in the current working directory.

def database(db_path):
	'''
	Establishes a connection to a SQLite database file and creates a table
	to store activity score results. 
	
	Parameters
	----------
	db_path: str
		Pathway to the SQLite database file.
	
	Returns
	-------
	None

	'''
	
	# the following command, sqlite3.connect(), creates a connection to
	# the database in the working directory, implicitly creating one if 
	# it does not exist already. 
	
	con = sqlite3.connect(db_path)
	
	# the following command, con.cursor(), creates a cursor to execute
	# SQL statements and fetch results from SQL queries.
	
	cur = con.cursor()
	
	# the following command, cur.execute(...), executes the 'CREATE
	# TABLE' statement. 
        
	cur.execute('CREATE TABLE activity_scores(Directed_Evolution_Generation, DNA_Quantification_fg, Protein_Quantification_pg, dna_baseline, protein_baseline, dna_corrected, protein_corrected, activity_score, Control)')

	# the following command, con.commit(), commits transactions, 
	# a necessary step before changes can be saved in the database. 
	
	con.commit()
	con.close()

# activity scores for each generation of a given variant
        
def compute_activity_score(df):
        '''
        Computes a generation-normalised Activity Score.
                        
        Activity Score is defined as baseline-corrected DNA yield divided by
        baseline-corrected protein yield:
                        
        DNA* = DNA(g, v) - DNA(g, control)
        Protein* = Protein(g, v) - Protein(g, control)
        ActivityScore = DNA*/ Protein*
                        
        Implementation Details:
        - A relative threshold is utilised, whereby there are two
          minimal values and the larger is implemented:
          The absolute minimal value (1e-6) prevents division by
          values close to zero. The other potential minimal value scales with
          the typical protein expression level - 5% is taken as
          below this threshold is typically noise.
                
        Parameters
        ----------
        df: DataFrame
                Input table containing DNA and Protein yield measurements
                for variants across generations. The dataframe must contain
                the following columns:
                - Plasmid_Variant_Index: str
                        Unique Identifier for each variant.
                - Directed_Evolution_Generation: int
                        Generation Identifier.
                - DNA_Quantification_fg: float
                        Measured DNA yield for each variant.
                - Protein_Quantification_pg: float
                        Measured protein expression level yield for each variant.
                - Control: bool
                        True for baseline control measurements.
                        False for variants.
                
        Returns
        -------
        scored_df: DataFrame
                Copy of the input dataframe with additional columns:
                - dna_baseline: float
                        Baseline DNA yield for the corresponding generation.
                - protein_baseline: float
                        Baseline protein yield for the corresponding
                        generation.
                - dna_corrected: float
                        Baseline-corrected DNA yield (DNA*).
                - protein_corrected: float
                        Baseline-corrected protein yield (Protein*).
                - activity_score: float
                        Generation-normalised Activity Score.
						
        '''
    
        required = {
                'Directed_Evolution_Generation',
                'DNA_Quantification_fg',
                'Protein_Quantification_pg',
                'Control'
        }
        
        # checkpoint
                
        missing = required - set(df.columns)
        if missing:
                raise ValueError(f'Missing Required Columns: {sorted(missing)}')
                
        # copy of the dataframe
                
        out = df.copy()

        # DNA and protein yield columns converted to numeric values
        # (ensures the values are not registered as string values)
                
        out['DNA_Quantification_fg'] = pd.to_numeric(out['DNA_Quantification_fg'], errors = 'coerce')
        out['Protein_Quantification_pg'] = pd.to_numeric(out['Protein_Quantification_pg'], errors = 'coerce')
                
        # checkpoint
        
        controls = out[out['Control'] == True]
        if controls.empty:
                raise ValueError('No control data found')
                        
        # baseline dna and protein yield values
        # (each generation's control experiments is grouped and then
        # the median value calculated)
                
        baselines = (
                controls.groupby('Directed_Evolution_Generation')
                .agg(
                        dna_baseline = ('DNA_Quantification_fg', 'median'),
                        protein_baseline = ('Protein_Quantification_pg', 'median'),
                     )
        )  
    
        # baseline values attached to each row
                
        out = out.merge(baselines, on = 'Directed_Evolution_Generation', how = 'right')
                
        # baseline-corrected DNA and baseline-corrected protein yield calculation
         
        out['dna_corrected'] = (out['DNA_Quantification_fg'] - out['dna_baseline'])
        
        r_protein = out['Protein_Quantification_pg'] - out['protein_baseline']
        r_min = sc_min * out['protein_baseline']
        protein_min = np.maximum(abs_min, r_min)
                
        # minimum allowed protein value enforced
        
        out['protein_corrected'] = np.where(r_protein < protein_min, protein_min, r_protein)
        
        # activity score calculation
        
        out['activity_score'] = out['dna_corrected']/ out['protein_corrected']
        out.loc[r_protein <= 0, 'activity_score'] = pd.NA
        
        return out


# writes activity scores to the SQLite database.

def write_activity_scores_to_db(scored_df, db_path):
	'''
	Writes computed activity score results to a SQLite database.
	'''
	required_cols = {
		'Directed_Evolution_Generation',
		'DNA_Quantification_fg',
		'Protein_Quantification_pg',
		'Control',
		'dna_baseline',
		'protein_baseline',
		'dna_corrected',
		'protein_corrected',
		'activity_score'
	}

	missing = set(required_cols) - set(scored_df.columns)
	if missing:
		raise ValueError(f'Scored DataFrame Missing Required Columns : {sorted(missing)}')

	with sqlite3.connect(db_path) as x:
		scored_df[list(required_cols)].to_sql(
			'activity_scores',
			x,
			if_exists='replace',
			index=False
		)
              
input_db_path = os.getenv('ACTIVITY_INPUT_DB_PATH')
if not input_db_path:
        input_db_path = resolve_db_path_from_url(os.getenv('DATABASE_URL'))
if not input_db_path:
        input_db_path = 'database.db'

input_table = os.getenv('ACTIVITY_INPUT_TABLE')
input_query = os.getenv('ACTIVITY_INPUT_QUERY')

x = load_input_from_db(
        db_path=input_db_path,
        source_table=input_table if not input_query else None,
        source_query=input_query
)
df = compute_activity_score(x)
debug_mode = os.getenv('ACTIVITY_DEBUG', '0').strip().lower() in {'1', 'true', 'yes'}
if debug_mode:
        print(df)

output_db_path = os.getenv('ACTIVITY_OUTPUT_DB_PATH', input_db_path)
write_activity_scores_to_db(df, output_db_path)

# how many are 'NaN'?   
y = df['activity_score'].isna().sum()
if debug_mode:
        print('There are', y, 'non-values')
        
# why are they 'NaN'?
z = df.loc[df['activity_score'].isna(), ['dna_corrected', 'protein_corrected', 'Control']]
if debug_mode:
        print(z)
                
a = df['dna_baseline']
if debug_mode:
        print(a)
                      
b = df.loc[df["Control"] == True, "dna_baseline"].describe()
if debug_mode:
        print(b)  
        
top_10 = df.sort_values(
        by = 'activity_score',
        ascending = False
).head(10)
         
if debug_mode:
        print(top_10)
if debug_mode:
        print(df["activity_score"].describe())
        
top_10_gen = top_10[
	['Directed_Evolution_Generation', 'activity_score']
]

if debug_mode:
        print(top_10_gen)
        
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.manifold import TSNE
from sklearn.decomposition import TruncatedSVD

# necessary columns for plot
var_col = 'Plasmid_Variant_Index'
seq_col = 'Protein_Sequence'
gen_col = 'Directed_Evolution_Generation'
prt_col = 'protein_corrected'
act_col = 'activity_score'

k = 3
initial_z_mode = os.getenv('ACTIVITY_Z_MODE', 'robust').strip().lower()
if initial_z_mode not in {'raw', 'normalized', 'robust'}:
        raise ValueError("ACTIVITY_Z_MODE must be 'raw', 'normalized', or 'robust'")

data = df[[var_col, seq_col, gen_col, prt_col, act_col,]].dropna().copy()

# make 2D coordinates from protein sequences using amino acid trigrams
X = CountVectorizer(analyzer = 'char', ngram_range=(k, k), lowercase = False).fit_transform(data[seq_col].astype(str))
embedding_method = os.getenv('ACTIVITY_EMBEDDING_METHOD', 'tsne').strip().lower()
if embedding_method not in {'tsne', 'pca'}:
        raise ValueError("ACTIVITY_EMBEDDING_METHOD must be 'tsne' or 'pca'")

cache_root = os.getenv(
        'ACTIVITY_EMBEDDING_CACHE_DIR',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance', 'embedding_cache')
)
os.makedirs(cache_root, exist_ok=True)

sig = hashlib.sha1()
sig.update(str(k).encode('utf-8'))
sig.update(embedding_method.encode('utf-8'))
for s in data[seq_col].astype(str).tolist():
        sig.update(s.encode('utf-8', errors='ignore'))
        sig.update(b'|')

if embedding_method == 'tsne':
        tsne_perplexity = float(os.getenv('ACTIVITY_TSNE_PERPLEXITY', '15'))
        tsne_max_iter = int(os.getenv('ACTIVITY_TSNE_MAX_ITER', '500'))
        sig.update(f'{tsne_perplexity}:{tsne_max_iter}'.encode('utf-8'))
        cache_file = os.path.join(cache_root, f'tsne_{sig.hexdigest()}.npy')
        if os.path.exists(cache_file):
                XY = np.load(cache_file)
        else:
                try:
                        XY = TSNE(
                                n_components=2,
                                perplexity=tsne_perplexity,
                                random_state=0,
                                init='pca',
                                learning_rate='auto',
                                max_iter=tsne_max_iter
                        ).fit_transform(X)
                except TypeError:
                        XY = TSNE(
                                n_components=2,
                                perplexity=tsne_perplexity,
                                random_state=0,
                                init='pca',
                                learning_rate='auto',
                                n_iter=tsne_max_iter
                        ).fit_transform(X)
                np.save(cache_file, XY)
else:
        sig.update(b'pca')
        cache_file = os.path.join(cache_root, f'pca_{sig.hexdigest()}.npy')
        if os.path.exists(cache_file):
                XY = np.load(cache_file)
        else:
                XY = TruncatedSVD(n_components=2, random_state=0).fit_transform(X)
                np.save(cache_file, XY)

data['x'] = XY[:, 0]
data['y'] = XY[:, 1]

grid_size = int(os.getenv('ACTIVITY_GRID_SIZE', '120'))
g_x = np.linspace(data['x'].min(), data['x'].max(), grid_size) 
g_y = np.linspace(data['y'].min(), data['y'].max(), grid_size) 

grid_x, grid_y = np.meshgrid(g_x, g_y)

# surface creation from activity score data 

def _display_transform(values, mode):
    """
    Transform z values for display mode.
    """
    if mode == 'raw':
        return values
    if mode == 'robust':
        lo = np.nanpercentile(values, 1)
        hi = np.nanpercentile(values, 99)
        if hi <= lo:
            return values
        return np.clip(values, lo, hi)
    out = (values - np.nanmin(values)) / (np.nanmax(values) - np.nanmin(values) + 1e-9)
    return out ** 1.3


def _mode_axis_title(mode):
    if mode == 'raw':
        return 'Activity Score'
    if mode == 'normalized':
        return 'Activity Score (Normalized)'
    return 'Activity Score (Robust-clipped)'


def _display_transform_with_bounds(values, mode, raw_min, raw_max, robust_lo, robust_hi):
    """
    Transform z values with global bounds so all generations are comparable.
    """
    if mode == 'raw':
        return values
    if mode == 'robust':
        return np.clip(values, robust_lo, robust_hi)
    out = (values - raw_min) / (raw_max - raw_min + 1e-9)
    return np.clip(out, 0, 1) ** 1.3


def surface(df, x_col, y_col, z_col, grid_x, grid_y, mode='raw'):
    """
    Generates an interpolated 3D surface from activity score data. 

    Parameters
    ----------
    df: DataFrame
        DataFrame containing the columns named as x_col, y_col and z_col.
       
    x_col: str
        Column representing x-coordinates (dimension 1 from SVD). 

    y_col: str
        Column representing y-coordinates
        (dimension 2 from SVD).

    z_col: str
        Name of the column representing z-values (activity score). 

    grid_x: array
        2D array defining x positions.

    grid_y: array
        2D array defining y positions.

    Returns
    -------
    array
        2D array of z-values. 
    """
    # points combination 
    points = np.column_stack([
        df[x_col].to_numpy(),
        df[y_col].to_numpy()
    ])

    # extract corresponding z values
    values = df[z_col].to_numpy()

    # linear interpolation (avoids overshoot spikes from cubic)
    z = griddata(points, values, (grid_x, grid_y), method='linear')

    # fill NaNs with nearest
    if np.isnan(z).any():
        z_near = griddata(points, values, (grid_x, grid_y), method='nearest')
        z = np.where(np.isnan(z), z_near, z)

    # Gaussian smoothing to produce a rolling mountain-range surface
    z = gaussian_filter(z, sigma=1.5)

    return z

# frames creation 

a = data 

a[gen_col] = pd.to_numeric(a[gen_col], errors = 'coerce')
frames = []

gens = sorted(a[gen_col].unique())
z_modes = ['robust', 'raw', 'normalized']

# global bounds used across all generations for stable comparisons
all_activity = a[act_col].to_numpy(dtype=float)
raw_min = float(np.nanmin(all_activity))
raw_max = float(np.nanmax(all_activity))
robust_lo = float(np.nanpercentile(all_activity, 1))
robust_hi = float(np.nanpercentile(all_activity, 99))


def _mode_range(mode):
    if mode == 'raw':
        return raw_min, raw_max
    if mode == 'robust':
        return robust_lo, robust_hi
    return 0.0, 1.0


def _frame_name(mode, generation):
    return f'{mode}:{generation}'

# minimum and maximum protein values for scale

min = a[prt_col].min()
min = int(min)

max = a[prt_col].max()
max = int(max)

for mode in z_modes:
	for x in gens:
		da_f = a[a[gen_col] <= x]
		z_raw = da_f[act_col].to_numpy()
		z_display = _display_transform_with_bounds(
			z_raw, mode, raw_min, raw_max, robust_lo, robust_hi
		)
		z_surface = _display_transform_with_bounds(
			surface(
				df=da_f,
				x_col='x',
				y_col='y',
				z_col=act_col,
				grid_x=grid_x,
				grid_y=grid_y,
				mode=mode
			),
			mode,
			raw_min,
			raw_max,
			robust_lo,
			robust_hi
		)
		mode_min, mode_max = _mode_range(mode)
		frames.append(go.Frame(
		name = _frame_name(mode, x),
		data = [
            go.Surface(
                x = g_x, 
                y = g_y, 
                z = z_surface, 
                opacity = 0.65,
                colorscale = 'Hot', 
                showscale = True,
                cmin = mode_min,
                cmax = mode_max,
                colorbar = dict(
                        title = _mode_axis_title(mode)
                )
	    ),
            go.Scatter3d(
                x = da_f['x'], 
		y = da_f['y'], 
		z = z_display,
		customdata = np.column_stack([
			da_f[var_col].to_numpy(),
			da_f[gen_col].to_numpy(),
			da_f[act_col].to_numpy()
		]),
		hovertemplate = (
				'Variant: %{customdata[0]}<br>' + 
				'Generation: %{customdata[1]}<br>' + 
				'Activity Score: %{customdata[2]: .3f}<br>' +
				'<extra></extra>'
		), 
                mode = 'markers',
                marker = dict(
			size = 4,
			opacity = 0.5,
			color = 'mediumpurple',
			)
            )
        ],
        layout=go.Layout(
                scene=dict(
                        zaxis_title=_mode_axis_title(mode),
                        zaxis=dict(range=[mode_min, mode_max])
                )
        )
    ))

# plot and slider 

raw_frame_names = [_frame_name('raw', x) for x in gens]
robust_frame_names = [_frame_name('robust', x) for x in gens]
norm_frame_names = [_frame_name('normalized', x) for x in gens]
initial_frame_name = _frame_name(initial_z_mode, gens[0])
initial_frame = next(f for f in frames if f.name == initial_frame_name)

fig = go.Figure(
	data = initial_frame.data, 
	frames = frames
)

fig.update_layout(
	title = '3D Activity Landscape',
	margin = dict(l = 0, r = 20, b = 0, t = 45),
	scene = dict(
		xaxis_title = 't-SNE Dim 1',
		yaxis_title = 't-SNE Dim 2',
		zaxis_title = _mode_axis_title(initial_z_mode),
		zaxis = dict(range=list(_mode_range(initial_z_mode)))
    ),
    scene_camera = dict(
        eye = dict(x = -1.8, y = -1.8, z = 1.2),
        up  = dict(x = 0, y = 0, z = 1)
    ),
    scene_aspectmode = 'manual',
    scene_aspectratio = dict(x=1, y=1, z=0.7),
    uirevision = 'keep',
    updatemenus = [dict(
        type = 'buttons',
        showactive = False,
        buttons = [
            dict(label = 'Play Robust', method = 'animate',
                 args = [robust_frame_names, {'frame': {'duration':500, 'redraw': True}, 'transition': {'duration': 200}}]),
            dict(label = 'Play Raw', method = 'animate',
                 args = [raw_frame_names, {'frame': {'duration':500, 'redraw': True}, 'transition': {'duration': 200}}]),
            dict(label = 'Play Normalized', method = 'animate',
                 args = [norm_frame_names, {'frame': {'duration':500, 'redraw': True}, 'transition': {'duration': 200}}]),
            dict(label = 'Robust', method = 'animate',
                 args = [[robust_frame_names[0]], {'mode': 'immediate', 'frame': {'duration': 0, 'redraw': True}}]),
            dict(label = 'Raw', method = 'animate',
                 args = [[raw_frame_names[0]], {'mode': 'immediate', 'frame': {'duration': 0, 'redraw': True}}]),
            dict(label = 'Normalized', method = 'animate',
                 args = [[norm_frame_names[0]], {'mode': 'immediate', 'frame': {'duration': 0, 'redraw': True}}]),
            dict(label = 'Stop', method = 'animate',
                 args = [[None], {'frame': {'duration': 0, 'redraw': False}, 'mode': 'immediate'}])
        ]
    )],
    sliders = [dict(
        currentvalue = dict(prefix = 'Frame: '),
        steps = [
                dict(
                        label = f'Robust G{int(x) if float(x).is_integer() else x}',
                        method = 'animate',
                        args = [[_frame_name("robust", x)], {'mode': 'immediate', 'frame': {'duration': 0, 'redraw': True}}]
                )
                for x in gens
        ] + [
                dict(
                        label = f'Raw G{int(x) if float(x).is_integer() else x}',
                        method = 'animate',
                        args = [[_frame_name("raw", x)], {'mode': 'immediate', 'frame': {'duration': 0, 'redraw': True}}]
                )
                for x in gens
        ] + [
                dict(
                        label = f'Norm G{int(x) if float(x).is_integer() else x}',
                        method = 'animate',
                        args = [[_frame_name("normalized", x)], {'mode': 'immediate', 'frame': {'duration': 0, 'redraw': True}}]
                )
                for x in gens
        ]
    )
])

fig.show()
	
if debug_mode:
        print(len(fig.data))
        print(type(fig.data[0]))
        print(type(fig.data[1]))
