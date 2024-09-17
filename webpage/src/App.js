import React, { useState, useEffect, useMemo } from 'react';
import {
  Container, Grid, Card, CardActionArea, CardActions, CardContent, CardMedia,
  Button, Typography, TextField, Dialog, DialogTitle, DialogContent,
  DialogContentText, DialogActions, Box, ThemeProvider, createTheme,
  Chip, FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import axios from 'axios';
import Fuse from 'fuse.js';
import debounce from 'lodash.debounce';
import List from 'list.js';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

function App() {
  const [models, setModels] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedModel, setSelectedModel] = useState(null);
  const [fuse, setFuse] = useState(null);
  const [categories, setCategories] = useState([]);
  const [tags, setTags] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [filteredModels, setFilteredModels] = useState([]);

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    if (models.length > 0) {
      const fuseOptions = {
        keys: ['model_name', 'description'],
        threshold: 0.4,
      };
      setFuse(new Fuse(models, fuseOptions));
      generateFilters();
    }
  }, [models]);

  const fetchModels = async () => {
    try {
      const response = await axios.get('printables_data.json');
      const modelArray = Object.entries(response.data).map(([id, model]) => ({
        id: parseInt(id),
        ...model
      }));
      setModels(modelArray);
    } catch (error) {
      console.error('Error fetching model data:', error);
    }
  };

  const generateTagsFromContent = (content) => {
    const stopwords = new Set(['the', 'layers', 'will', 'like', 'filament', 'need', 'round', 'speed', 'guide', 'temperature', 'created', 'make', 'support', 'recommended', 'without', 'inside', 'printing', 'sure', 'holes', 'check', 'your', 'more', 'layer', 'printed', 'have', 'used', 'flat', 'surface','a', 'an', 'print', 'model', 'of', 'the', 'then', 'there', 'other', 'base', 'height', 'some', 'infill', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'it', 'as', 'from', 'that', 'this', 'are', 'was', 'were', 'be', 'has', 'had', 'not', 'they', 'he', 'she', 'www', 'http', 'https', 'com', 'net', 'org']);
    const words = content.toLowerCase().split(/\W+/);
    return [...new Set(words.filter(word => word.length > 3 && !stopwords.has(word) && isNaN(word)))];
  };

  const generateFilters = () => {
    const allCategories = [...new Set(models.map(model => model.category))];
    setCategories(allCategories);
  
    const allTags = models.reduce((acc, model) => {
      const contentTags = [
        ...generateTagsFromContent(model.model_name),
        ...generateTagsFromContent(model.description)
      ];
      return [...acc, ...contentTags];
    }, []);
  
    const tagCounts = allTags.reduce((acc, tag) => {
      acc[tag] = (acc[tag] || 0) + 1;
      return acc;
    }, {});
  
    const popularTags = Object.entries(tagCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([tag]) => tag);
  
    setTags(popularTags);
  };

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  const handleCategoryChange = (event) => {
    setSelectedCategory(event.target.value);
  };

  const handleTagClick = (tag) => {
    setSelectedTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  const handleCardClick = (model) => {
    setSelectedModel(model);
  };

  const handleCloseDialog = () => {
    setSelectedModel(null);
  };

  const debouncedSearch = useMemo(
    () => debounce((searchTerm, selectedCategory, selectedTags) => {
      const filtered = models
        .filter(model => 
          (!selectedCategory || model.category === selectedCategory) &&
          (selectedTags.length === 0 || selectedTags.every(tag => {
            const modelTags = [
              ...generateTagsFromContent(model.model_name),
              ...generateTagsFromContent(model.description)
            ];
            return modelTags.includes(tag);
          }))
        )
        .filter(model => 
          !searchTerm || (fuse && fuse.search(searchTerm).some(result => result.item.id === model.id))
        );
      setFilteredModels(filtered);
    }, 300),
    [models, fuse]
  );

  useEffect(() => {
    debouncedSearch(searchTerm, selectedCategory, selectedTags);
    return () => {
      debouncedSearch.cancel();
    };
  }, [searchTerm, selectedCategory, selectedTags, debouncedSearch]);

  const renderSearchAndFilters = () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 4, mt: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
          <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search models"
            value={searchTerm}
            onChange={handleSearchChange}
            sx={{
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              '& .MuiOutlinedInput-root': {
                borderRadius: '20px',
              }
            }}
          />
        </Box>
        <FormControl variant="outlined" sx={{ minWidth: 120 }}>
          <InputLabel>Category</InputLabel>
          <Select
            value={selectedCategory}
            onChange={handleCategoryChange}
            label="Category"
            sx={{
              borderRadius: '20px',
              '& .MuiOutlinedInput-notchedOutline': {
                borderRadius: '20px',
              }
            }}
          >
            <MenuItem value="">
              <em>None</em>
            </MenuItem>
            {categories.map(category => (
              <MenuItem key={category} value={category}>{category}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {tags.map(tag => (
          <Chip
            key={tag}
            label={tag}
            onClick={() => handleTagClick(tag)}
            color={selectedTags.includes(tag) ? "primary" : "default"}
          />
        ))}
      </Box>
    </Box>
  );

  const renderModelCard = (model) => (
    <Grid item xs={12} sm={6} md={4} lg={3} xl={2} key={model.id}>
      <Card elevation={3} sx={{
        borderRadius: '15px',
        '&:hover': {
          transform: 'scale(1.05)',
          transition: 'transform 0.3s',
        },
      }}>
        <CardActionArea onClick={() => handleCardClick(model)}>
          <CardMedia
            component="img"
            height="200"
            image={model.first_image_url}
            alt={model.model_name}
          />
          <CardContent>
            <Typography gutterBottom variant="h6" component="h2">
              {model.model_name}
            </Typography>
            <Typography variant="body2" color="text.secondary" noWrap>
              {model.description}
            </Typography>
          </CardContent>
        </CardActionArea>
        <CardActions>
          <Button size="small" color="primary" href={model.download_link} target="_blank">
            Download
          </Button>
        </CardActions>
      </Card>
    </Grid>
  );

  const renderDialog = () => (
    <Dialog 
      open={selectedModel !== null} 
      onClose={handleCloseDialog} 
      maxWidth="md" 
      fullWidth
      PaperProps={{
        sx: {
          backgroundColor: 'background.paper',
          color: 'text.primary',
          width: '800px',
          height: '500px',
          borderRadius: '20px',
        }
      }}
    >
      {selectedModel && (
        <Box sx={{ display: 'flex', height: '100%' }}>
          <Box sx={{ width: '50%', p: 2 }}>
            <img 
              src={selectedModel.first_image_url} 
              alt={selectedModel.model_name} 
              style={{ 
                width: '100%', 
                height: '100%', 
                objectFit: 'cover', 
                borderRadius: '15px' 
              }} 
            />
          </Box>
          <Box sx={{ width: '50%', p: 2, display: 'flex', flexDirection: 'column' }}>
            <DialogTitle sx={{ p: 0, mb: 2 }}>{selectedModel.model_name}</DialogTitle>
            <DialogContent sx={{ p: 0, flex: 1, overflowY: 'auto' }}>
              <DialogContentText color="text.secondary">
                {selectedModel.description}
              </DialogContentText>
            </DialogContent>
            <DialogActions sx={{ p: 0, mt: 2 }}>
              <Button onClick={handleCloseDialog} color="primary">
                Close
              </Button>
              <Button href={selectedModel.download_link} target="_blank" color="primary" variant="contained">
                Download
              </Button>
            </DialogActions>
          </Box>
        </Box>
      )}
    </Dialog>
  );

  return (
    <ThemeProvider theme={darkTheme}>
      <Container maxWidth="xl" sx={{ mt: 4, px: { xs: 1, sm: 2, md: 3 } }}>
        {renderSearchAndFilters()}
        <Grid container spacing={3}>
          {filteredModels.map(renderModelCard)}
        </Grid>
      </Container>
      {renderDialog()}
    </ThemeProvider>
  );
}

export default App;